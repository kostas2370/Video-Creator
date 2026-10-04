from rest_framework import serializers

from .models import (
    ApiKeys,
    UserCustomTTSProvider,
    UserCustomVisualProvider,
    AuthType,
    Provider,
)

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


class CustomProviderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    reserved_provider_names = ()

    def validate_extra_parameters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Extra parameters must be a JSON object.")
        return value

    def validate_name(self, value):
        if value.casefold() in {
            name.casefold() for name in self.reserved_provider_names
        }:
            raise serializers.ValidationError(
                "This name is reserved for a built-in provider."
            )
        if self.instance and value != self.instance.name:
            raise serializers.ValidationError(
                "The provider name cannot be changed after creation."
            )
        return value

    def validate(self, attrs):
        auth_type = attrs.get(
            "auth_type", getattr(self.instance, "auth_type", AuthType.BEARER)
        )
        header = attrs.get(
            "auth_header_name", getattr(self.instance, "auth_header_name", "")
        )
        if auth_type == AuthType.HEADER and not header:
            raise serializers.ValidationError(
                {
                    "auth_header_name": "Header name is required when auth_type is set to 'header'.",
                }
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["api_key"] = ApiKeys.mask(instance.api_key)
        return data

    class Meta:
        extra_kwargs = {
            "api_key": {"write_only": True, "required": False, "allow_blank": True},
        }


class UserCustomTTSProviderSerializer(CustomProviderSerializer):
    reserved_provider_names = (Provider.OPENAI, Provider.ELEVENLABS, Provider.SIXTYDB)
    voices_url = serializers.URLField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta(CustomProviderSerializer.Meta):
        model = UserCustomTTSProvider
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=UserCustomTTSProvider.objects.all(),
                fields=("user", "name"),
                message="You already have a custom provider with this name.",
            ),
        ]
        fields = (
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
            "extra_parameters",
        )


class UserCustomVisualProviderSerializer(CustomProviderSerializer):
    reserved_provider_names = (
        Provider.OPENAI,
        Provider.STABLE_DIFFUSION,
        Provider.MIDJOURNEY,
        "DALL-E",
        "sora",
        "stable-diffusion",
        "midjourney",
        "bing",
        "google",
    )

    class Meta(CustomProviderSerializer.Meta):
        model = UserCustomVisualProvider
        fields = (
            "id",
            "user",
            "name",
            "output_type",
            "endpoint_url",
            "auth_type",
            "auth_header_name",
            "api_key",
            "prompt_field_name",
            "extra_parameters",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=UserCustomVisualProvider.objects.all(),
                fields=("user", "name"),
                message="You already have a custom visual provider with this name.",
            ),
        ]
