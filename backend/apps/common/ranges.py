"""Parse one HTTP byte range independently of authentication and streaming."""

import re


def parse_byte_range(header, size):
    """Return inclusive (start, end), None for no range, or raise ValueError."""
    if not header:
        return None
    match = re.fullmatch(r"bytes=([0-9]{0,20})-([0-9]{0,20})", header.strip())
    if not match or not any(match.groups()):
        raise ValueError("Invalid byte range.")
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
    elif int(last) > 0:
        start, end = max(0, size - int(last)), size - 1
    else:
        raise ValueError("Invalid byte range.")
    if start >= size or start > end:
        raise ValueError("Unsatisfiable byte range.")
    return start, end
