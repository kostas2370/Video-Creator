from apps.videomanagement.throttling import BaseThrottle


class PublishingThrottle(BaseThrottle):
    scope = "social_publish"
    rate = "20/hour"


class ConnectionThrottle(BaseThrottle):
    scope = "social_connect"
    rate = "10/hour"


class ContextThrottle(BaseThrottle):
    scope = "social_context"
    rate = "15/minute"


class StatusThrottle(BaseThrottle):
    scope = "social_status"
    rate = "12/minute"
