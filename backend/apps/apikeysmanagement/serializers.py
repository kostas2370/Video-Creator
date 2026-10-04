from rest_framework import serializers

from .models import ApiKeys, UserCustomTTSProvider, AuthType

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


class UserCustomTTSProviderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = UserCustomTTSProvider
        fields = [
            "id",
            "user",
            "name",
            "endpoint_url",
            "auth_type",
            "auth_header_name",
            "api_key",
            "voices_url",
            "text_field_name",
            "voice_field_name",
        ]
        extra_kwargs = {
            # Hide api_key from read responses for security
            "api_key": {"write_only": True},
        }

    def validate(self, attrs):
        auth_type = attrs.get("auth_type", getattr(self.instance, "auth_type", None))
        auth_header_name = attrs.get(
            "auth_header_name",
            getattr(self.instance, "auth_header_name", ""),
        )

        if auth_type == AuthType.HEADER and not auth_header_name:
            raise serializers.ValidationError(
                {
                    "auth_header_name": (
                        "Header name is required when auth_type is set to 'header'."
                    )
                }
            )

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["api_key"] = ApiKeys.mask(instance.api_key)
        return data
