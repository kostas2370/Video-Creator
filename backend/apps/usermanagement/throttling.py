from rest_framework.throttling import AnonRateThrottle


class ContactThrottle(AnonRateThrottle):
    rate = "5/hour"
