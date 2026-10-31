SENTENCE_ENDINGS = (".", "!", "?", "…", "。", "！", "？")
TRAILING_QUOTES = "\"'”’»)]}"
MAX_EXTENSION_SECONDS = 5
PAUSE_SECONDS = 0.8


def is_boundary(words, index):
    if index == 0 or index == len(words):
        return True
    previous, following = words[index - 1], words[index]
    return previous["text"].rstrip(TRAILING_QUOTES).endswith(SENTENCE_ENDINGS) or (
        following["start"] - previous["end"] >= PAUSE_SECONDS
    )


def refine_boundaries(words, first, last, minimum, maximum):
    original = first, last
    while first > 0 and not is_boundary(words, first):
        if (
            words[original[0]]["start"] - words[first - 1]["start"]
            > MAX_EXTENSION_SECONDS
        ):
            first = original[0]
            break
        first -= 1
    while last + 1 < len(words) and not is_boundary(words, last + 1):
        if words[last + 1]["end"] - words[original[1]]["end"] > MAX_EXTENSION_SECONDS:
            last = original[1]
            break
        last += 1
    if minimum <= words[last]["end"] - words[first]["start"] <= maximum:
        return first, last
    return original
