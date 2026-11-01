import json
import logging
from pathlib import Path
from decimal import Decimal, InvalidOperation

from django.conf import settings

logger = logging.getLogger(__name__)
_CATALOG = json.loads(
    Path(__file__).with_name("pricing.json").read_text(encoding="utf-8")
)
PRICING_DATE = _CATALOG["checked_at"]
OPENAI_SOURCE = _CATALOG["sources"]["image_tokens"]
IMAGE_SOURCE = _CATALOG["sources"]["image_reference"]
DEFAULT_RATES = _CATALOG["rates"]
IMAGE_REFERENCE_PRICES = _CATALOG["image_reference_prices"]
IMAGE_TOKEN_RATES = _CATALOG["image_token_rates_per_million"]


def money(value):
    return format(value, ".8f") if value is not None else None


def rate_for(service, provider, model, *, custom=False):
    key = f"{service}:{provider}:{model}"
    overrides = getattr(settings, "AI_COST_RATES", {})
    if not isinstance(overrides, dict):
        overrides = {}
    rate = (
        overrides.get(key)
        if key in overrides
        else None
        if custom
        else DEFAULT_RATES.get(key)
    )
    if not isinstance(rate, dict):
        return None
    return {"checked_at": PRICING_DATE, **rate}


def unit_cost(rate, measurements):
    if not rate:
        return None
    units = (
        "characters",
        "images",
        "seconds",
        "requests",
        "input_tokens",
        "output_tokens",
    )
    try:
        priced = [unit for unit in units if unit in rate]
        if not priced or any(measurements.get(unit) is None for unit in priced):
            return None
        values = [Decimal(str(rate[unit])) for unit in priced]
        if any(not value.is_finite() or value < 0 for value in values):
            return None
        return sum(
            (measurements[unit] * value for unit, value in zip(priced, values)),
            Decimal(0),
        )
    except (InvalidOperation, ValueError, TypeError):
        logger.warning("Invalid AI cost rate; estimate unavailable")
        return None


def measured_cost(service, provider, model, measurements, usage=None, *, custom=False):
    rate = rate_for(service, provider, model, custom=custom)
    if rate:
        return unit_cost(rate, measurements), rate
    if (
        custom
        or service != "images"
        or provider != "OPENAI"
        or model not in IMAGE_TOKEN_RATES
    ):
        return None, {}

    def get(obj, name):
        return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)

    details = get(usage, "input_tokens_details")
    text, images, output = (
        get(details, "text_tokens"),
        get(details, "image_tokens"),
        measurements.get("output_tokens"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (text, images, output)
    ):
        return None, {}
    prices = tuple(
        IMAGE_TOKEN_RATES[model][unit]
        for unit in ("text_input", "image_input", "image_output")
    )
    cost = sum(
        (
            Decimal(value) * Decimal(price) / 1_000_000
            for value, price in zip((text, images, output), prices)
        ),
        Decimal(0),
    )
    return cost, {
        "checked_at": PRICING_DATE,
        "source": OPENAI_SOURCE,
        "text_input_usd_per_million": prices[0],
        "image_input_usd_per_million": prices[1],
        "image_output_usd_per_million": prices[2],
        "basis": "Reported text/image input and image output tokens; excludes cache discounts.",
    }


def estimate_line(label, service, provider, model, measurements, *, custom=False):
    rate = rate_for(service, provider, model, custom=custom)
    cost = unit_cost(rate, {"requests": 1, **measurements})
    return {
        "label": label,
        "service": service,
        "provider": provider,
        "model": model,
        "units": measurements,
        "low_usd": money(cost),
        "high_usd": money(cost),
        "source": (rate or {}).get("source", ""),
        "checked_at": (rate or {}).get("checked_at", PRICING_DATE),
        "note": ""
        if cost is not None
        else "Price unavailable for this provider and model.",
    }


def tts_estimate(text, provider, model="", *, requests=1, custom=False):
    return estimate_line(
        "Narration",
        "tts",
        provider,
        model,
        {"characters": len(text), "requests": requests},
        custom=custom,
    )


def image_estimate(count, provider="OPENAI", model=None, *, custom=False, quality=None):
    model = model or (
        settings.IMAGE_MODEL if provider == "OPENAI" and not custom else ""
    )
    line = estimate_line(
        "Images",
        "images",
        provider,
        model,
        {"images": count, "requests": count},
        custom=custom,
    )
    if line["low_usd"] is not None or custom or provider != "OPENAI":
        return line
    quality = quality or settings.IMAGE_QUALITY
    prices = IMAGE_REFERENCE_PRICES.get(model, {}).get(quality)
    if prices:
        line.update(
            low_usd=money(Decimal(prices["low_usd"]) * count),
            high_usd=money(Decimal(prices["high_usd"]) * count),
            source=IMAGE_SOURCE,
            note=f"{quality.title()} quality: output-only guide for 1024-square and 1024×1536 reference sizes. Your frame size, prompt and reference images change the final cost.",
        )
    return line


def total_estimate(lines):
    known = [line for line in lines if line["low_usd"] is not None]
    return {
        "currency": _CATALOG["currency"],
        "lines": lines,
        "partial": len(known) != len(lines)
        or any(line.get("partial", False) for line in lines),
        "low_usd": money(sum((Decimal(line["low_usd"]) for line in known), Decimal(0)))
        if known or not lines
        else None,
        "high_usd": money(
            sum((Decimal(line["high_usd"]) for line in known), Decimal(0))
        )
        if known or not lines
        else None,
        "checked_at": PRICING_DATE,
    }
