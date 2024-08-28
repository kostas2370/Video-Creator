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


