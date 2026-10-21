"""Official provider endpoints. Errors deliberately omit tokens and response bodies."""

from datetime import timedelta
from urllib.parse import urlencode, urlparse

import requests
from django.utils import timezone
from django.db import transaction

from .models import SocialAccount

from .config import callback_url, require_configured
from .models import Platform


class ProviderError(Exception):
    pass


def api(method, url, token=None, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, url, headers=headers, timeout=(10, 90), allow_redirects=False, **kwargs)
        if not 200 <= response.status_code < 300:
            raise ProviderError("The platform rejected the request. Check the account permissions and posting settings.")
        data = response.json()
        if not isinstance(data, dict):
            raise ProviderError("The platform returned an unexpected response.")
        error = data.get("error")
        if error and (not isinstance(error, dict) or error.get("code") not in (None, "ok", 0)):
            raise ProviderError("The platform could not complete the request. Check account permissions and posting limits.")
        return data
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError("The platform request did not complete. Check its status before trying another upload.") from exc


def meta_base():
    return "https://graph.facebook.com/" + require_configured(Platform.INSTAGRAM)["api_version"]


def authorization_url(platform, state):
    config = require_configured(platform)
    values = {"redirect_uri": callback_url(platform), "state": state, "response_type": "code"}
    if platform == Platform.YOUTUBE:
        endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        values.update(client_id=config["client_id"], access_type="offline", prompt="consent",
                      scope="https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly")
    elif platform == Platform.TIKTOK:
        endpoint = "https://www.tiktok.com/v2/auth/authorize/"
        values.update(client_key=config["client_id"], scope="user.info.basic,video.publish")
    else:
        endpoint = "https://www.facebook.com/" + config["api_version"] + "/dialog/oauth"
        values.update(client_id=config["client_id"], scope="pages_show_list,instagram_basic,instagram_content_publish,pages_read_engagement")
    return endpoint + "?" + urlencode(values)


def exchange_code(platform, code):
    config = require_configured(platform)
    values = {"client_secret": config["client_secret"], "code": code, "redirect_uri": callback_url(platform)}
    if platform == Platform.YOUTUBE:
        return api("POST", "https://oauth2.googleapis.com/token", data={**values, "client_id": config["client_id"], "grant_type": "authorization_code"})
    if platform == Platform.TIKTOK:
        return api("POST", "https://open.tiktokapis.com/v2/oauth/token/", data={**values, "client_key": config["client_id"], "grant_type": "authorization_code"})
    short = api("GET", meta_base() + "/oauth/access_token", params={**values, "client_id": config["client_id"]})
    return api("GET", meta_base() + "/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": config["client_id"],
        "client_secret": config["client_secret"], "fb_exchange_token": short["access_token"],
    })


def identities(platform, tokens):
    token = tokens["access_token"]
    if platform == Platform.YOUTUBE:
        data = api("GET", "https://www.googleapis.com/youtube/v3/channels", token,
                   params={"part": "snippet", "mine": "true"})
        if len(data.get("items", [])) != 1:
            raise ProviderError("Choose one YouTube channel during account authorization and connect it again.")
        return [{"external_id": row["id"], "display_name": row["snippet"]["title"], "access_token": token}
                for row in data.get("items", [])]
    if platform == Platform.TIKTOK:
        data = api("GET", "https://open.tiktokapis.com/v2/user/info/", token,
                   params={"fields": "open_id,display_name"})["data"]["user"]
        return [{"external_id": data["open_id"], "display_name": data["display_name"], "access_token": token}]
    result = []
    endpoint = meta_base() + "/me/accounts"
    params = {"fields": "name,access_token,instagram_business_account{id,username}", "limit": 100}
    # Cursors, not provider-supplied URLs, keep credentials on the known Graph host.
    for _ in range(20):
        data = api("GET", endpoint, token, params=params)
        for page in data.get("data", []):
            profile = page.get("instagram_business_account")
            if profile:
                result.append({"external_id": profile["id"], "display_name": profile.get("username") or page["name"],
                               "access_token": page["access_token"]})
        paging = data.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not paging.get("next") or not after:
            break
        params["after"] = after
    return result


@transaction.atomic
def access_token(account):
    account = SocialAccount.objects.select_for_update().get(pk=account.pk)
    if account.expires_at and account.expires_at <= timezone.now() + timedelta(minutes=2):
        config = require_configured(account.platform)
        if not account.refresh_token or account.platform == Platform.INSTAGRAM:
            raise ProviderError("This account connection has expired. Reconnect it before publishing.")
        values = {"client_secret": config["client_secret"], "refresh_token": account.refresh_token, "grant_type": "refresh_token"}
        if account.platform == Platform.YOUTUBE:
            tokens = api("POST", "https://oauth2.googleapis.com/token", data={**values, "client_id": config["client_id"]})
        else:
            tokens = api("POST", "https://open.tiktokapis.com/v2/oauth/token/", data={**values, "client_key": config["client_id"]})
        account.access_token = tokens["access_token"]
        account.refresh_token = tokens.get("refresh_token") or account.refresh_token
        account.expires_at = timezone.now() + timedelta(seconds=int(tokens.get("expires_in", 3600)))
        account.save(update_fields=["access_token", "refresh_token", "expires_at"])
    return account.access_token


def creator_info(account):
    result = api("POST", "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
                 access_token(account), json={})
    return result["data"]


def checked_upload_url(url, platform):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = host == "www.googleapis.com" if platform == Platform.YOUTUBE else host.endswith(".tiktokapis.com")
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
    if parsed.scheme != "https" or not allowed or not valid_port or parsed.username or parsed.password:
        raise ProviderError("The platform returned an unsupported upload address.")
    return url
