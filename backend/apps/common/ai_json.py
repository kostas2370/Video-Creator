"""Read JSON returned by text-mode AI providers."""

import json
import re


def parse_ai_json(raw):
    """Accept plain JSON, Markdown fences, or prose surrounding a JSON object."""
    if not isinstance(raw, str):
        raise ValueError("Expected a JSON response string.")
    text = re.sub(r"^```[a-z]*\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Do not turn a malformed array into one of its nested objects.
        if text.startswith("["):
            raise
        return json.loads(text[text.index("{") : text.rindex("}") + 1])
