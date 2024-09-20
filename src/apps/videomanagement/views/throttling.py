from rest_framework.throttling import UserRateThrottle


class GenerateRateThrottle(UserRateThrottle):
    rate = '1/hour'


class TwitchGenerateRateThrottle(UserRateThrottle):
    rate = '2/hour'
