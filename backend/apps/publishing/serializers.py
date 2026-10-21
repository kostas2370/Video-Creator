from rest_framework import serializers

from .models import PublishJob, SocialAccount


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ["id", "platform", "display_name", "expires_at"]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishJob
        fields = ["id", "video", "platform", "account_name", "status", "url", "error", "created_at"]


class PublishSerializer(serializers.Serializer):
    account = serializers.UUIDField()
    video = serializers.UUIDField()
    request_id = serializers.UUIDField()
    export_updated_at = serializers.DateTimeField()
    title = serializers.CharField(max_length=100, allow_blank=True, default="")
    caption = serializers.CharField(max_length=5000, allow_blank=True, default="")
    privacy = serializers.CharField(max_length=50, allow_blank=True, default="")
    made_for_kids = serializers.BooleanField(required=False)
    synthetic = serializers.BooleanField(default=False)
    allow_comment = serializers.BooleanField(default=False)
    allow_duet = serializers.BooleanField(default=False)
    allow_stitch = serializers.BooleanField(default=False)
    own_brand = serializers.BooleanField(default=False)
    branded_content = serializers.BooleanField(default=False)
    music_consent = serializers.BooleanField(default=False)
    share_to_feed = serializers.BooleanField(default=False)
    confirmed = serializers.BooleanField()

    def validate_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Review the video and confirm before publishing.")
        return value
