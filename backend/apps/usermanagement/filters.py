from apps.common.filters import UserFilterSet


class NotificationFilter(UserFilterSet):
    @staticmethod
    def unread_count(queryset):
        return queryset.filter(read=False).count()
