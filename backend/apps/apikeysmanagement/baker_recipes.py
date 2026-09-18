from model_bakery.recipe import Recipe, foreign_key

from .models import ApiKeys

api_keys = Recipe(
    ApiKeys,
    user=foreign_key("usermanagement.user"),
    openai_key="sk-user-openai-key",
    elevenlabs_key="user-elevenlabs-key",
)
