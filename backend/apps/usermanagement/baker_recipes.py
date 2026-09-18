from model_bakery.recipe import Recipe, seq

from .models import User

user = Recipe(
    User,
    username=seq("user"),
    email=seq("user", suffix="@example.test"),
    first_name="Test",
    last_name="User",
    is_verified=True,
    generation_limit_for_ai=100.0,
    generation_limit_for_twitch=100.0,
)

broke_user = user.extend(
    generation_limit_for_ai=0.0,
    generation_limit_for_twitch=0.0,
)

superuser = user.extend(is_superuser=True, is_staff=True)
