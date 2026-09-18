from rest_framework import serializers

from .models import ApiKeys

KEY_FIELDS = (
    "openai_key",
    "anthropic_key",
    "gemini_key",
    "elevenlabs_key",
    "sixtydb_key",
    "diffusion_key",
    "midjourney_key",
    "google_search_key",
    "google_search_engine_id",
    "twitch_client_id",
    "twitch_client_secret",
)


class ApiKeysSerializer(serializers.ModelSerializer):
    use_service_api_keys = serializers.BooleanField(
        source="user.use_service_api_keys", required=False
    )

    class Meta:
        model = ApiKeys
        fields = ("id", "updated_at", "use_service_api_keys", *KEY_FIELDS)
        read_only_fields = ("id", "updated_at")
        extra_kwargs = {
            field: {
                "write_only": True,
                "required": False,
                "allow_blank": True,
                "trim_whitespace": True,
                "style": {"input_type": "password"},
            }
            for field in KEY_FIELDS
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for field in KEY_FIELDS:
            data[field] = ApiKeys.mask(getattr(instance, field, ""))

        return data

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "use_service_api_keys" in user_data:
            instance.user.use_service_api_keys = user_data["use_service_api_keys"]
            instance.user.save(update_fields=["use_service_api_keys"])

        return super().update(instance, validated_data)
