"""Fallback source-word timing shared by the editor, preview and exports."""
import re


def estimated_words(text, duration):
    tokens = re.findall(r"\S{1,40}", text or "")
    total, consumed = sum(len(token) for token in tokens), 0
    words = []
    for token in tokens:
        start = duration * consumed / total
        consumed += len(token)
        words.append({"text": token, "start": start, "end": duration * consumed / total})
    return words


def validate_word_bounds(words, duration):
    from rest_framework.exceptions import ValidationError

    previous_end = 0
    for word in words:
        if word["start"] < previous_end or word["end"] > duration:
            raise ValidationError("Keep words in order, without overlaps, and within the source audio duration.")
        previous_end = word["end"]
    return words
