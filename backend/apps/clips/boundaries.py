SENTENCE_ENDINGS = (".", "!", "?", ";", ";", "…", "。", "！", "？")
TRAILING_QUOTES = "\"'”’»)]}"
MAX_ADJUSTMENT_SECONDS = 5
PAUSE_SECONDS = 0.8


def is_boundary(words, index):
    if index == 0 or index == len(words):
        return True
    previous, following = words[index - 1], words[index]
    return previous["text"].rstrip(TRAILING_QUOTES).endswith(SENTENCE_ENDINGS) or (
        following["start"] - previous["end"] >= PAUSE_SECONDS
    )


def refine_boundaries(words, first, last, minimum, maximum):
    """Prefer complete edges, preserving selected speech before minimizing movement."""
    start, end = words[first]["start"], words[last]["end"]
    starts, ends = [first], [last]
    # Leave an already clean edge alone. Search both ways so a nearby sentence
    # can still fit when extending both ends would exceed the duration limit.
    if not is_boundary(words, first):
        index = first - 1
        while index >= 0 and start - words[index]["start"] <= MAX_ADJUSTMENT_SECONDS:
            if is_boundary(words, index):
                starts.append(index)
            index -= 1
        index = first + 1
        while index <= last and words[index]["start"] - start <= MAX_ADJUSTMENT_SECONDS:
            if is_boundary(words, index):
                starts.append(index)
            index += 1
    if not is_boundary(words, last + 1):
        index = last + 1
        while index < len(words) and words[index]["end"] - end <= MAX_ADJUSTMENT_SECONDS:
            if is_boundary(words, index + 1):
                ends.append(index)
            index += 1
        index = last - 1
        while index >= first and end - words[index]["end"] <= MAX_ADJUSTMENT_SECONDS:
            if is_boundary(words, index + 1):
                ends.append(index)
            index -= 1

    best, best_score = (first, last), None
    for opening in starts:
        for closing in ends:
            new_start, new_end = words[opening]["start"], words[closing]["end"]
            if opening > closing or not minimum <= new_end - new_start <= maximum:
                continue
            clean_edges = int(is_boundary(words, opening)) + int(
                is_boundary(words, closing + 1)
            )
            removed = max(0, new_start - start) + max(0, end - new_end)
            movement = abs(new_start - start) + abs(new_end - end)
            score = (clean_edges, -removed, -movement)
            if best_score is None or score > best_score:
                best, best_score = (opening, closing), score
    return best
