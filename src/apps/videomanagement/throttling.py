from rest_framework.throttling import UserRateThrottle


class BaseThrottle(UserRateThrottle):

    def allow_request(self, request, view):
        if request.user.is_superuser:
            return True

        return super().allow_request(request, view)


class GenerateRateThrottle(BaseThrottle):
    rate = '2/hour'


class TwitchGenerateRateThrottle(BaseThrottle):
    rate = '6/hour'


class RenderRateThrottle(BaseThrottle):
    rate = '1/day'
