from rest_framework.exceptions import ValidationError

from apps.common.ai_json import parse_ai_json
from apps.videomanagement.integrations.llm import get_reply
from apps.videomanagement.serializers.ideas import (
    IdeaResultSerializer,
    PromptResultSerializer,
)
from apps.videomanagement.utils.prompt_utils import (
    build_ideas_prompt,
    build_prompt_rewrite,
)


def generate_ideas(user, *, gpt_model="", **brief):
    response = get_reply(
        build_ideas_prompt(brief),
        reply_format="text",
        gpt_model=gpt_model or None,
        user=user,
    )
    try:
        result = IdeaResultSerializer(data=parse_ai_json(response.getvalue()))
        result.is_valid(raise_exception=True)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise ValidationError("AI returned invalid ideas. Please try again.") from exc
    return dict(result.validated_data)


def rewrite_prompt(user, *, gpt_model="", **brief):
    response = get_reply(
        build_prompt_rewrite(brief),
        reply_format="text",
        gpt_model=gpt_model or None,
        user=user,
    )
    try:
        result = PromptResultSerializer(data=parse_ai_json(response.getvalue()))
        result.is_valid(raise_exception=True)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise ValidationError(
            "AI returned an invalid rewrite. Please try again."
        ) from exc
    return dict(result.validated_data)
