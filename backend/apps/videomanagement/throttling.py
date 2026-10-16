from rest_framework.throttling import UserRateThrottle


class CloneVoiceThrottle(UserRateThrottle):
    scope = "clone_voice"
    rate = "5/hour"


class VoicePreviewThrottle(UserRateThrottle):
    scope = "voice_preview"
    rate = "20/hour"


class BaseThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        if request.user.is_superuser:
            return True

        return super().allow_request(request, view)


class GenerateRateThrottle(BaseThrottle):
    scope = "generate"
    rate = "2/hour"


class ResumeRateThrottle(BaseThrottle):
    scope = "resume"
    rate = "2/hour"


class RenderRateThrottle(BaseThrottle):
    scope = "render"
    rate = "1/day"
