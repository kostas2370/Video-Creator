from django.urls import reverse
from rest_framework import serializers

from apps.videomanagement.models import Video, VideoShare


class ShareOptionsSerializer(serializers.Serializer):
    expires_in_days = serializers.ChoiceField(
        choices=VideoShare.ExpiryDays.choices, allow_null=True, default=None
    )


class VideoShareSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    path = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    expiry_options = serializers.SerializerMethodField()

    def get_expiry_options(self, share):
        return [
            {"value": None, "label": "Never"},
            *(
                {"value": value, "label": label}
                for value, label in VideoShare.ExpiryDays.choices
            ),
        ]


def share_details(share):
    active = share is not None and share.active
    return VideoShareSerializer(
        {
            "active": active,
            "path": f"/share/{share.token}/" if active else None,
            "expires_at": share.expires_at if active else None,
        }
    ).data


class PublicVideoSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ["title", "description", "tags", "media_url"]

    def get_tags(self, video):
        return list(
            dict.fromkeys(
                tag
                for group in video.tags.values()
                if isinstance(group, list)
                for tag in group
                if isinstance(tag, str) and tag.strip()
            )
        )

    def get_media_url(self, video):
        return self.context["request"].build_absolute_uri(
            reverse("shared-video-media", args=[self.context["token"]])
        )
