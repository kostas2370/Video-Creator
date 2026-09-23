from rest_framework.permissions import SAFE_METHODS, BasePermission
from .models import Scene, SceneImage, Video


class IsOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if isinstance(obj, Scene):
            obj = Video.objects.filter(prompt_id=obj.prompt_id).first()

        if isinstance(obj, SceneImage):
            obj = Video.objects.filter(prompt_id=obj.scene.prompt_id).first()

        if obj is None:
            return False

        return obj.created_by == request.user or request.user.is_superuser


class IsOwnerOrReadOnlyPermission(IsOwnerPermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return super().has_object_permission(request, view, obj)


class BaseGenerationLimitPermission(BasePermission):
    limit_field = None
    required_limit = 1
    message = "You do not have enough tokens !"

    def has_permission(self, request, view) -> bool:
        if not self.limit_field:
            raise NotImplementedError(
                f"{self.__class__.__name__} requires a `limit_field` attribute."
            )

        if not request.user.is_authenticated:
            return False

        generation_limit = getattr(request.user, self.limit_field, 0)
        return request.user.is_superuser or generation_limit > self.required_limit


class AiGenerationLimitPermission(BaseGenerationLimitPermission):
    limit_field = "generation_limit_for_ai"


class TwitchGenerationLimitPermission(BaseGenerationLimitPermission):
    limit_field = "generation_limit_for_twitch"
    required_limit = 0.6


class SceneGenerationLimitPermission(BaseGenerationLimitPermission):
    limit_field = "generation_limit_for_ai"
    required_limit = 0.2


class SceneImageGenerationLimitPermission(BaseGenerationLimitPermission):
    limit_field = "generation_limit_for_ai"
    required_limit = 0.4
