from rest_framework.permissions import SAFE_METHODS, BasePermission
from .models import Scene, SceneImage


class IsOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if isinstance(obj, Scene):
            obj = obj.video

        if isinstance(obj, SceneImage):
            obj = obj.scene.video

        if obj is None:
            return False

        return obj.created_by_id == request.user.pk or request.user.is_superuser


class IsOwnerOrReadOnlyPermission(IsOwnerPermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return super().has_object_permission(request, view, obj)
