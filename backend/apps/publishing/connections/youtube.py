"""YouTube authorization, channel discovery and token renewal."""

from urllib.parse import urlencode

from ..config import callback_url, require_configured
from ..http import ProviderError, api
from ..models import Platform

TOKEN_URL = "https://oauth2.googleapis.com/token"


def authorization_url(state):
    config = require_configured(Platform.YOUTUBE)
    values = {
        "client_id": config["client_id"],
        "redirect_uri": callback_url(Platform.YOUTUBE),
        "state": state, "response_type": "code",
        "access_type": "offline", "prompt": "consent",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(values)


def exchange_code(code):
    config = require_configured(Platform.YOUTUBE)
    payload = {
        "client_id": config["client_id"], "client_secret": config["client_secret"],
        "code": code, "redirect_uri": callback_url(Platform.YOUTUBE),
        "grant_type": "authorization_code",
    }
    return api("POST", TOKEN_URL, data=payload)


def refresh_token(token):
    config = require_configured(Platform.YOUTUBE)
    payload = {
        "client_id": config["client_id"], "client_secret": config["client_secret"],
        "refresh_token": token, "grant_type": "refresh_token",
    }
    return api("POST", TOKEN_URL, data=payload)


def identities(tokens):
    token = tokens["access_token"]
    data = api(
        "GET", "https://www.googleapis.com/youtube/v3/channels", token=token,
        params={"part": "snippet", "mine": "true"},
    )
    if len(data.get("items", [])) != 1:
        raise ProviderError("Choose one YouTube channel during account authorization and connect it again.")
    row = data["items"][0]
    return [{"external_id": row["id"], "display_name": row["snippet"]["title"], "access_token": token}]
