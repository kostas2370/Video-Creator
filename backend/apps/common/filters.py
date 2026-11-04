from rest_framework.filters import BaseFilterBackend


class OwnerFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        field = getattr(view, "owner_field", "created_by")
        return queryset.filter(**{field: request.user})


class OwnerOrSuperuserFilterBackend(OwnerFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            return queryset
        return super().filter_queryset(request, queryset, view)
