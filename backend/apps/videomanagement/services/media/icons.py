"""Local catalog search shared by the AI planner and the editor."""

import re
from functools import reduce
from operator import or_

from django.db.models import Case, IntegerField, Q, Value, When

from apps.videomanagement.models import Icon
from apps.videomanagement.utils.file_utils import stored_file_exists

STOP_WORDS = set("the and for are was were has had not but can could more than then create make video videos scene scenes image images animation animated educational explain explainer english tiktok exactly about with from that this into your their they them only should would have will use using every each first last seconds total narration script labels avatar generated portrait format readable captions short show shows please topic".split())
COMMON_ICONS = ("lucide:droplet", "lucide:cloud", "lucide:sun", "lucide:zap", "lucide:leaf", "lucide:heart", "lucide:cpu", "lucide:factory", "lucide:truck", "lucide:package", "lucide:network", "lucide:circle")


def search_icons(query="", *, keys=None, user=None, queryset=None):
    icons = Icon.objects.all() if queryset is None else queryset
    icons = icons.filter(Q(created_by__isnull=True) | Q(created_by=user), enabled=True).exclude(file="")
    if keys is not None:
        return icons.filter(key__in=keys)
    words = list(dict.fromkeys(word.rstrip("s") for word in re.findall(r"[^\W\d_]{3,}", query.lower()) if word not in STOP_WORDS))[:20]
    if not words:
        return icons
    score = Value(0, output_field=IntegerField())
    matches = []
    for word in words:
        # Match the beginning of a word: bank finds banknote, interest avoids Pinterest.
        pattern = rf"(^|[^\w]){re.escape(word)}"
        name = Q(name__iregex=pattern)
        description = Q(description__iregex=pattern)
        score += Case(When(name, then=Value(4)), default=Value(0))
        score += Case(When(description, then=Value(1)), default=Value(0))
        matches.append(name | description)
    return icons.filter(reduce(or_, matches)).annotate(relevance=score).order_by("-relevance", "collection", "name", "key")


def icon_candidates(query, limit=60, *, user=None):
    """Send a bounded relevant shortlist, never the whole catalog, to the language model."""
    if limit <= 0:
        return []
    ranked = list(search_icons(query, user=user)[:max(1, limit - len(COMMON_ICONS))])
    common = list(search_icons(keys=COMMON_ICONS, user=user))
    found = {icon.key: icon for icon in [*ranked, *common] if stored_file_exists(icon.file)}
    return [{"id": icon.key, "name": icon.name, "description": icon.description[:180]}
            for icon in list(found.values())[:limit]]


def available_icon_files(keys, *, user=None):
    return {icon.key: icon.file for icon in search_icons(keys=keys, user=user) if stored_file_exists(icon.file)}
