"""Recipe for a user with keys of their own.

Only the providers the tests actually read are pinned; the rest stay blank, which is
also the shape of a real row — nobody pays for every provider at once.
"""

from model_bakery.recipe import Recipe, foreign_key

from .models import ApiKeys

api_keys = Recipe(
    ApiKeys,
    # Reuses the account recipe the rest of the suite owns rather than a second idea
    # of what a user looks like.
    user=foreign_key("usermanagement.user"),
    openai_key="sk-user-openai-key",
    elevenlabs_key="user-elevenlabs-key",
)
