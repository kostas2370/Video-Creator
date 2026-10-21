"""Meta authorization and discovery of Instagram professional accounts."""

from urllib.parse import urlencode

from ..config import callback_url, require_configured
from ..http import request_json
from ..models import Platform


def meta_base():
    return "https://graph.facebook.com/" + require_configured(Platform.INSTAGRAM)["api_version"]


def authorization_url(state):
    config = require_configured(Platform.INSTAGRAM)
    values = {
        "client_id": config["client_id"], "redirect_uri": callback_url(Platform.INSTAGRAM),
        "state": state, "response_type": "code",
        "scope": "pages_show_list,instagram_basic,instagram_content_publish,pages_read_engagement",
    }
    return f"https://www.facebook.com/{config['api_version']}/dialog/oauth?" + urlencode(values)


def exchange_code(code):
    config = require_configured(Platform.INSTAGRAM)
    payload = {
        "client_id": config["client_id"], "client_secret": config["client_secret"],
        "code": code, "redirect_uri": callback_url(Platform.INSTAGRAM),
    }
    short = request_json("GET", f"{meta_base()}/oauth/access_token", params=payload)
    return request_json("GET", f"{meta_base()}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": config["client_id"],
        "client_secret": config["client_secret"], "fb_exchange_token": short["access_token"],
    })


def identities(tokens):
    token = tokens["access_token"]
    result = []
    endpoint = meta_base() + "/me/accounts"
    params = {"fields": "name,access_token,instagram_business_account{id,username}", "limit": 100}
    # Cursors, not provider-supplied URLs, keep credentials on the known Graph host.
    for _ in range(20):
        data = request_json("GET", endpoint, token, params=params)
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

