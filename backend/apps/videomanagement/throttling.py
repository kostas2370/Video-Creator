from rest_framework.throttling import UserRateThrottle


class BaseThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        if request.user.is_superuser:
            return True

        return super().allow_request(request, view)


class GenerateRateThrottle(BaseThrottle):
    scope = "generate"
    rate = "2/hour"


class TwitchGenerateRateThrottle(BaseThrottle):
    scope = "twitch_generate"
    rate = "6/hour"


class ResumeRateThrottle(BaseThrottle):
    scope = "resume"
    rate = "2/hour"


class RenderRateThrottle(BaseThrottle):
    scope = "render"
    rate = "1/day"
