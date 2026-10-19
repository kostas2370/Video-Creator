"""Fallback source-word timing shared by the editor, preview and exports."""

import math
import re

from rest_framework.exceptions import ValidationError


def estimated_words(text, duration):
    tokens = re.findall(r"\S{1,40}", text or "")
    total, consumed = sum(len(token) for token in tokens), 0
    words = []
    for token in tokens:
        start = duration * consumed / total
        consumed += len(token)
        words.append(
            {"text": token, "start": start, "end": duration * consumed / total}
        )
    return words


def validate_word_bounds(words, duration):
    previous_end = 0
    for word in words:
        if word["start"] < previous_end or word["end"] > duration:
            raise ValidationError(
                "Keep words in order, without overlaps, and within the source audio duration."
            )
        previous_end = word["end"]
    return words


def normalize_words(items, duration):
    words, previous_end = [], 0
    for item in items or []:
        start, end = float(item.start), float(item.end)
        if not math.isfinite(start) or not math.isfinite(end):
            continue
        start, end = max(previous_end, 0, start), min(duration, end)
        tokens = re.findall(r"\S{1,40}", item.word.strip())
        if not tokens or end <= start:
            continue
        for index, token in enumerate(tokens):
            token_start = round(start + (end - start) * index / len(tokens), 4)
            token_end = min(
                duration, round(start + (end - start) * (index + 1) / len(tokens), 4)
            )
            if token_end > token_start and token_end <= duration:
                words.append({"text": token, "start": token_start, "end": token_end})
        previous_end = end
    return words
