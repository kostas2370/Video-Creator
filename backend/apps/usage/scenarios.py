import math

from django.conf import settings

from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.utils.prompt_utils import build_script_prompt

from .models import AIUsage
from .pricing import estimate_line, money, total_estimate


def scenario_estimate(data, user):
    model = data.get("gpt_model") or settings.DEFAULT_GPT_MODEL
    provider = (
        "ANTHROPIC"
        if model.startswith("claude")
        else "GEMINI"
        if model.startswith("gemini")
        else "OPENAI"
    )
    if not model.startswith(("claude", "gemini", "gpt", "o1", "o3", "o4")):
        model = settings.DEFAULT_GPT_MODEL
    prompt = build_script_prompt(
        userprompt=data["message"],
        genre=data.get("genre", ""),
        target_audience=data.get("target_audience", ""),
        platform=data.get("platform", "GENERAL"),
        scene_count=data.get("scene_count"),
        image_mode=data.get("image_mode", "WEB"),
        video=ImageProviderRegistry.is_video(
            data.get("provider"), user=user, mode=data.get("image_mode", "WEB")
        ),
        style=data.get("style", "natural"),
        narration=data.get("narration", True),
        ai_scene_editing=data.get("ai_scene_editing", False),
        visual_continuity=data.get("visual_continuity", ""),
        reference_role=data.get("reference_role", "both")
        if data.get("has_reference")
        else None,
    )
    budget = settings.MAX_TOKENS + (
        settings.REASONING_TOKEN_ALLOWANCE if provider == "OPENAI" else 0
    )
    low = estimate_line(
        "Scenario / script",
        "text",
        provider,
        model,
        {
            "input_tokens": math.ceil(len(prompt) / 4),
            "output_tokens": min(
                budget, max(500, (data.get("scene_count") or 8) * 300)
            ),
        },
    )
    high = estimate_line(
        "Scenario / script",
        "text",
        provider,
        model,
        {"input_tokens": math.ceil(len(prompt) / 2), "output_tokens": budget},
    )
    low["high_usd"] = high["high_usd"]
    low["units"] = {"requests": 1}
    low["note"] = (
        "Planning range using the assembled prompt, roughly 2–4 characters per input token, and expected script output through the configured output budget. Reasoning, language, reference images, series context and retries can change the charge; this is not a spending cap."
    )
    result = total_estimate([low])
    result.update(
        scope="scenario",
        note="Scenario drafting only. Images, animation and narration are estimated after storyboard review.",
    )
    return result


def missing_scenario_line():
    line = estimate_line(
        "Scenario / script (already drafted)",
        "text",
        "Unrecorded",
        "",
        {"requests": 0},
        custom=True,
    )
    line["note"] = (
        "Scenario cost is unavailable for earlier project requests. It is excluded from the known subtotal; proceeding does not draft it again."
    )
    return line


def recorded_scenario_line(video):
    usage = AIUsage.objects.filter(
        user_id=video.created_by_id, video=video, service="text"
    ).summary()
    totals = usage["totals"]
    if not totals["requests"]:
        return missing_scenario_line()
    line = {
        "label": "Scenario / script (already drafted)",
        "service": "text",
        "provider": "Recorded project requests",
        "model": ", ".join(
            sorted({row["model"] for row in usage["breakdown"] if row["model"]})
        ),
        "units": {"requests": totals["requests"]},
        "low_usd": money(totals["cost_usd"]),
        "high_usd": money(totals["cost_usd"]),
        "note": "Already incurred; proceeding only generates the remaining media.",
        "source": "",
        "partial": totals["requests_with_cost"] < totals["requests"],
    }
    if line["partial"]:
        line["note"] += (
            f" Only {totals['requests_with_cost']} of {totals['requests']} script requests are priced."
        )
    return line


def include_scenario(estimate, line):
    result = {
        **estimate,
        **total_estimate([*estimate["lines"], line]),
        "scope": "generation",
    }
    result["note"] = (
        "Includes scenario costs already incurred and one planned media pass. Additional rewrites, retries, taxes and discounts are excluded."
    )
    return result


def project_estimate(video, storyboard=None):
    from .estimates import media_estimate

    estimate = media_estimate(video, storyboard)
    return (
        include_scenario(estimate, recorded_scenario_line(video))
        if video.video_type != "MANUAL"
        else estimate
    )
