from apps.videomanagement.throttling import BaseThrottle


class ClipProcessingThrottle(BaseThrottle):
    scope = "clip_processing"
    rate = "10/hour"
