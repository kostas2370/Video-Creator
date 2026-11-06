from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter, SearchFilter


class BaseFilterSet(filters.FilterSet):
    """Apply access scoping even when no query parameters are supplied."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.scope_queryset(self.queryset)

    @property
    def action(self):
        context = getattr(self.request, "parser_context", None) or {}
        return getattr(context.get("view"), "action", None)

    def scope_queryset(self, queryset):
        return queryset


class OwnerFilterSet(BaseFilterSet):
    owner_field = "created_by"

    def scope_queryset(self, queryset):
        if self.request is None:
            return queryset.none()
        return queryset.filter(**{self.owner_field: self.request.user})


class UserFilterSet(OwnerFilterSet):
    owner_field = "user"


class OwnerOrSuperuserFilterSet(OwnerFilterSet):
    def scope_queryset(self, queryset):
        if self.request is not None and self.request.user.is_superuser:
            return queryset
        return super().scope_queryset(queryset)


class SearchFilterSet(BaseFilterSet):
    search = filters.CharFilter(method="filter_search")
    search_fields = ()

    def filter_search(self, queryset, name, value):
        return SearchFilter().filter_queryset(self.request, queryset, self)


class SearchOrderingFilterSet(SearchFilterSet):
    ordering = filters.CharFilter(method="filter_ordering")
    default_ordering = ("id",)

    def filter_ordering(self, queryset, name, value):
        # Preserve DRF's public-serializer field allowlist and invalid-field behavior.
        ordering = OrderingFilter().get_ordering(self.request, queryset, self)
        return queryset.order_by(*(ordering or self.default_ordering))
