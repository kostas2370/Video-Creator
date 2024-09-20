from rest_framework.permissions import BasePermission
from .models import Scene, SceneImage, Videos


class IsOwnerPermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated and not request.user.is_active:
            return False

        if isinstance(obj, Scene):
            obj = Videos.objects.get(prompt_id = obj.prompt.id)

        if isinstance(obj, SceneImage):
            obj = Videos.objects.get(prompt_id = obj.scene.prompt.id)

        return obj.created_by == request.user or request.user.is_superuser


class BaseGenerationLimitPermission(BasePermission):

    limit_field = None
    required_limit = 1
    message = "You do not have enough tokens !"

    def has_permission(self, request, view):
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
