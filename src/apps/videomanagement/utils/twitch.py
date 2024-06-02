from django.conf import settings
import requests
from .exceptions import GameNotFound, InvalidTwitchToken, StreamerNotFound, HeaderInitiationError
import urllib.request
import uuid


class TwitchClient:
    """
        A client for interacting with the Twitch API to fetch game and streamer information, clips, and download clips.

        Attributes:
        -----------
        path : str
            The directory path where downloaded clips will be saved.
        headers : dict or None
            The headers for authentication, including the Bearer token and Client ID.
        """

    def __init__(self, path):
        """
        Initialize the TwitchClient with a specified path for downloading clips.

        Parameters:
        -----------
        path : str
            The directory path where downloaded clips will be saved.
        """

        self.path = path
        self.headers = None

    def set_headers(self) -> dict:
        """
        Set the headers required for Twitch API requests by obtaining an OAuth token.

        Returns:
        --------
        dict
        The headers containing the Bearer token and Client ID.

        Raises:
        -------
        requests.exceptions.HTTPError
        If an HTTP error occurs during the request for the OAuth token.
            requests.exceptions.RequestException
                    If a general error occurs during the request for the OAuth token.
        """

        headers = {'Content-Type': 'application/x-www-form-urlencoded', }
        data = f'client_id={settings.TWITCH_CLIENT}&client_secret={settings.TWITCH_CLIENT_SECRET}' \
               f'&grant_type=client_credentials'

        try:
            response = requests.post('https://id.twitch.tv/oauth2/token', headers = headers, data = data)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            return err

        except requests.exceptions.RequestException as err:
            return err

        bearer = response.json()['access_token']
        self.headers = {"Authorization": f"Bearer {bearer}", "Client-Id": settings.TWITCH_CLIENT}
        return {"Authorization": f"Bearer {bearer}", "Client-Id": settings.TWITCH_CLIENT}

    def get_game_id(self, name: str) -> str:
        """
        Retrieve the game ID for a given game name.

        Parameters:
        -----------
        name : str
            The name of the game.

        Returns:
        --------
        str
            The ID of the game.

        Raises:
        -------
        HeaderInitiationError
            If headers have not been initialized.
        GameNotFound
            If the game is not found.
        InvalidTwitchToken
            If the Twitch token is invalid.
        """

        if self.headers is None:
            raise HeaderInitiationError

        url = f"https://api.twitch.tv/helix/games?name={name}"
        req = requests.get(url, headers = self.headers)
        if req.status_code == 400:
            raise GameNotFound

        if req.status_code == 401:
            raise InvalidTwitchToken

        return req.json().get("data")[0].get("id")

    def get_streamer_id(self, name: str) -> str:
        """
        Retrieve the streamer ID for a given streamer name.

        Parameters:
        -----------
        name : str
            The name of the streamer.

        Returns:
        --------
        str
            The ID of the streamer.

        Raises:
        -------
        StreamerNotFound
            If the streamer is not found.
        InvalidTwitchToken
            If the Twitch token is invalid.
        """

        url = f'https://api.twitch.tv/helix/users?login={name}'
        req = requests.get(url, headers = self.headers)
        if req.status_code == 400:
            raise StreamerNotFound

        if req.status_code == 401:
            raise InvalidTwitchToken

        return req.json().get("data").get("id")

    def get_clips(self, value: str, mode="game", start_date: str = ""):
        """
        Retrieve the streamer ID for a given streamer name.

        Parameters:
        -----------
        name : str
            The name of the streamer.

        Returns:
        --------
        str
            The ID of the streamer.

        Raises:
        -------
        StreamerNotFound
            If the streamer is not found.
        InvalidTwitchToken
            If the Twitch token is invalid.
        """

        base_url = "https://api.twitch.tv/helix/clips"

        url = f"{base_url}?game_id={value}" if mode == "game" else \
              f"{base_url}?broadcaster_id={value}"

        if start_date:
            url += f"&started_at={start_date}T00:00:00Z"

        clips = requests.get(url, headers = self.headers)

        return clips.json().get("data")

    def download_clip(self, clip) -> str:
        """
        Download a clip and save it to the specified directory.

        Parameters:
        -----------
        clip : dict
            The clip data containing the 'thumbnail_url'.

        Returns:
        --------
        str
            The file path to the downloaded clip.
        """

        index = clip.get("thumbnail_url").find('-preview')
        filename = f'{str(uuid.uuid4())}.mp4'
        urllib.request.urlretrieve(clip['thumbnail_url'][:index]+".mp4", f'{self.path}\\{filename}')

        return f'{self.path}\\{filename}'
