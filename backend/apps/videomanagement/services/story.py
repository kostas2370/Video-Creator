"""Draft narration for Story mode without creating a project or audio."""
import json
import re

from rest_framework.exceptions import APIException, ValidationError

from ..serializers.requests import StoryDraftResultSerializer
from ..utils.llm import get_update_sentence


def draft_story(user, prompt):
    instructions = (
        "Create a story draft following the user's prompt below. "
        "Return ONLY a JSON object with title (at most 50 characters) and story "
        "(plain narration only, no headings, scene directions, hashtags, or markdown). "
        "The story must fit the editor's limit of 2000 characters.\nUser prompt: "
        + json.dumps(prompt, ensure_ascii=False)
    )
    reply = get_update_sentence(instructions, user=user)
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip())
        result = json.loads(cleaned)
        serializer = StoryDraftResultSerializer(data=result)
        serializer.is_valid(raise_exception=True)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise APIException("AI returned an invalid story draft. Please try again.") from exc
    return dict(serializer.validated_data)
