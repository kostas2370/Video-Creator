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


class StoryDraftRateThrottle(BaseThrottle):
    scope = "story_draft"
    rate = "15/hour"


class CaptionRateThrottle(BaseThrottle):
    scope = "caption_processing"
    rate = "10/hour"


class ResumeRateThrottle(BaseThrottle):
    scope = "resume"
    rate = "2/hour"


class RenderRateThrottle(BaseThrottle):
    scope = "render"
    rate = "1/day"


class TagGenerationRateThrottle(BaseThrottle):
    scope = "tag_generation"
    rate = "15/hour"


class CoverGenerationRateThrottle(BaseThrottle):
    scope = "cover_generation"
    rate = "10/hour"


class RenderRetryRateThrottle(BaseThrottle):
    scope = "render_retry"
    rate = "3/hour"
