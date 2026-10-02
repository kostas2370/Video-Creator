from model_bakery.recipe import Recipe, foreign_key

from .models import ApiKeys, UserCustomTTSProvider, AuthType

api_keys = Recipe(
    ApiKeys,
    user=foreign_key("usermanagement.user"),
    openai_key="sk-user-openai-key",
    elevenlabs_key="user-elevenlabs-key",
)

user_custom_tts_provider = Recipe(
    UserCustomTTSProvider,
    user=foreign_key("usermanagement.user"),
    name="my_custom_tts",
    endpoint_url="https://api.customtts.com/v1/synthesize",
    auth_type=AuthType.BEARER,
    api_key="secret-api-key",
    text_field_name="input_text",
    voice_field_name="voice_id",
)