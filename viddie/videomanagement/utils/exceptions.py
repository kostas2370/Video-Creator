"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


class InvalidJsonFormatError(Exception):

    def __init__(self):
        self.message = "Invalid Json Format"


class FileNotDownloadedError(Exception):

    def __init__(self):
        self.message = "could not download the video"


class GameNotFound(Exception):
    def __init__(self):
        self.message = "Could not find a game with that name"


class StreamerNotFound(Exception):
    def __init__(self):
        self.message = "Could not find a streamer with that name"


class InvalidTwitchToken(Exception):
    def __init__(self):
        self.message = "Invalid Twitch Token"


class HeaderInitiationError(Exception):
    def __init__(self):
        self.message = "You need to set headers !"


