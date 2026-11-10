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


def _validated_reply(prompt, serializer_class, error_message, *, user, gpt_model):
    response = get_reply(
        prompt,
        reply_format="text",
        gpt_model=gpt_model or None,
        user=user,
    )
    try:
        result = serializer_class(data=parse_ai_json(response.getvalue()))
        result.is_valid(raise_exception=True)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise ValidationError(error_message) from exc
    return dict(result.validated_data)


def generate_ideas(user, *, gpt_model="", **brief):
    return _validated_reply(
        build_ideas_prompt(brief),
        IdeaResultSerializer,
        "AI returned invalid ideas. Please try again.",
        user=user,
        gpt_model=gpt_model,
    )


def rewrite_prompt(user, *, gpt_model="", **brief):
    return _validated_reply(
        build_prompt_rewrite(brief),
        PromptResultSerializer,
        "AI returned an invalid rewrite. Please try again.",
        user=user,
        gpt_model=gpt_model,
    )
