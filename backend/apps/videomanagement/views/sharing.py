from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clips.protected_media import media_response
from apps.videomanagement.serializers.sharing import (
    PublicVideoSerializer,
    ShareOptionsSerializer,
    share_details,
)
from apps.videomanagement.services.videos.sharing import (
    create_video_share,
    get_shared_video,
    get_video_share,
    revoke_video_share,
)


class VideoShareMixin:
    @action(detail=True, methods=["GET"], url_path="share")
    def share(self, request, pk=None):
        share = get_video_share(self.get_object())
        return Response(share_details(share), headers={"Cache-Control": "no-store"})

    @share.mapping.post
    def create_share(self, request, pk=None):
        video = self.get_object()
        options = ShareOptionsSerializer(data=request.data)
        options.is_valid(raise_exception=True)
        share = create_video_share(video, **options.validated_data)
        return Response(share_details(share), headers={"Cache-Control": "no-store"})

    @share.mapping.delete
    def revoke_share(self, request, pk=None):
        revoke_video_share(self.get_object())
        return Response(status=204)


class PublicVideoShareView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Referrer-Policy"] = "no-referrer"
        return response

    def get(self, request, token, media=False):
        video = get_shared_video(token)
        if media:
            return media_response(request, video.output)
        return Response(
            PublicVideoSerializer(
                video,
                context={"request": request, "token": token},
            ).data
        )
