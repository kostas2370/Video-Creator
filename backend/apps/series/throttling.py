from apps.videomanagement.throttling import BaseThrottle


class SeriesMemoryRateThrottle(BaseThrottle):
    scope = "series_memory"
    rate = "15/hour"
