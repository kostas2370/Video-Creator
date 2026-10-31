from apps.videomanagement.throttling import BaseThrottle


class SeriesMemoryRateThrottle(BaseThrottle):
    scope = "series_memory"
    rate = "15/hour"


class SeriesCastDraftRateThrottle(BaseThrottle):
    scope = "series_cast_draft"
    rate = "15/hour"


class CharacterImageRateThrottle(BaseThrottle):
    scope = "character_image"
    rate = "30/hour"
