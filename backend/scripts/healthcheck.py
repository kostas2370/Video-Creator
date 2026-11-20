"""Probe the private API using its configured host and HTTPS proxy contract."""

import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

host = urlparse(os.getenv("FRONTEND_URL") or "").netloc or "localhost"
request = Request(
    "http://127.0.0.1:8000/api/health/ready/",
    headers={"Host": host, "X-Forwarded-Proto": "https"},
)
with urlopen(request, timeout=12) as response:
    if response.status != 200:
        raise SystemExit(1)
