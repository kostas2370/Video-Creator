from rest_framework.exceptions import ValidationError

from apps.common.ai_json import parse_ai_json
from apps.videomanagement.integrations.llm import get_reply


def creative_reply(user, *, prompt, serializer_class, error_message, gpt_model=""):
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
