"""TikTok authorization, creator discovery and token renewal."""

from urllib.parse import urlencode

from ..config import callback_url, require_configured
from ..http import request_json
from ..models import Platform

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def authorization_url(state):
    config = require_configured(Platform.TIKTOK)
    values = {
        "client_key": config["client_id"], "redirect_uri": callback_url(Platform.TIKTOK),
        "state": state, "response_type": "code", "scope": "user.info.basic,video.publish",
    }
    return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(values)


def exchange_code(code):
    config = require_configured(Platform.TIKTOK)
    payload = {
        "client_key": config["client_id"], "client_secret": config["client_secret"],
        "code": code, "redirect_uri": callback_url(Platform.TIKTOK),
        "grant_type": "authorization_code",
    }
    return request_json("POST", TOKEN_URL, data=payload)


def refresh_token(token):
    config = require_configured(Platform.TIKTOK)
    payload = {
        "client_key": config["client_id"], "client_secret": config["client_secret"],
        "refresh_token": token, "grant_type": "refresh_token",
    }
    return request_json("POST", TOKEN_URL, data=payload)


def identities(tokens):
    token = tokens["access_token"]
    data = request_json(
        "GET", "https://open.tiktokapis.com/v2/user/info/", token=token,
        params={"fields": "open_id,display_name"},
    )["data"]["user"]
    return [{"external_id": data["open_id"], "display_name": data["display_name"], "access_token": token}]


def creator_info(token):
    return request_json(
        "POST", "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
        token=token, json={},
    )["data"]
