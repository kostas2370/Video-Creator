from django.conf import settings
import requests
from .exceptions import GameNotFound, InvalidTwitchToken, StreamerNotFound, HeaderInitiationError
import urllib.request
import uuid


class TwitchClient:

    def __init__(self, path):
        self.path = path
        self.headers = None

    def set_headers(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded', }
        data = f'client_id={settings.CLIENT_iD}&client_secret={settings.CLIENT_SECRET}&grant_type=client_credentials'

        try:
            response = requests.post('https://id.twitch.tv/oauth2/token', headers = headers, data = data)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            return err

        except requests.exceptions.RequestException as err:
            return err

        bearer = response.json()['access_token']
        return {"Authorization": f"Bearer {bearer}", "Client-Id": settings.CLIENT_ID}

    def get_game_id(self, name):
        if self.headers is None:
            raise HeaderInitiationError

        url = f"https://api.twitch.tv/helix/games?name={name}"
        req = requests.get(url, headers = self.headers)
        if req.status_code == 400:
            raise GameNotFound

        if req.status_code == 401:
            raise InvalidTwitchToken

        return req.json().get("data").get("id")

    def get_streamer_id(self, name):

        url = f'https://api.twitch.tv/helix/users?login={name}'
        req = requests.get(url, headers = self.headers)
        if req.status_code == 400:
            raise StreamerNotFound

        if req.status_code == 401:
            raise InvalidTwitchToken

        return req.json().get("data").get("id")

    def get_clips(self, value, mode="game"):
        base_url = "https://api.twitch.tv/helix/clips"

        url = f"{base_url}?game_id={value}" if mode == "game" else \
              f"{base_url}?broadcaster_id={value}"

        clips = requests.get(url, headers = self.headers)

        return clips.json().get("data")

    def download_clip(self, clip):
        index = clip.get("thumbnail_url").find('-preview')
        clip_url = clip.thumbnail_url[:index]+'.mp4'
        filename = f'{str(uuid.uuid4())}.mp4'
        urllib.request.urlretrieve(clip_url, f'{self.path}\\{filename}.mp4')

        return f'{self.path}\\{filename}.mp4'
