import hashlib
import time
from collections.abc import Mapping

from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, BaseThrottle

from .models import Login


class ContactThrottle(AnonRateThrottle):
    rate = "5/hour"


class LoginThrottle(BaseThrottle):
    """Atomic fixed-window counters shared by production workers through Redis."""

    scope = "login"

    def identities(self, request):
        identities = [("ip", Login.get_user_ip(request) or "unknown", 60, 10)]
        username = (
            request.data.get("username") if isinstance(request.data, Mapping) else None
        )
        if isinstance(username, str) and username.strip():
            identities.append(("account", username.strip().casefold(), 300, 10))
        return identities

    def allow_request(self, request, view):
        self.retry_after = 0
        now = time.time()
        for scope, identity, window, limit in self.identities(request):
            digest = hashlib.sha256(identity.encode()).hexdigest()
            key = f"{self.scope}:{scope}:{digest}:{int(now // window)}"
            if cache.add(key, 1, timeout=window + 1):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:  # Window expired between add and incr.
                    cache.add(key, 1, timeout=window + 1)
                    count = 1
            if count > limit:
                self.retry_after = max(self.retry_after, window - now % window)
        return not self.retry_after

    def wait(self):
        return self.retry_after


class RegistrationThrottle(LoginThrottle):
    scope = "registration"

    def identities(self, request):
        return [("ip", Login.get_user_ip(request) or "unknown", 3600, 5)]
