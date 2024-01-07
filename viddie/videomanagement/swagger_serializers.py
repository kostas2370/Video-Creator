"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


from rest_framework import serializers
from .models import TEMPLATE_CHOICES


class GenerateSerializer(serializers.Serializer):
    message = serializers.CharField(required = True, max_length = 2000)
    template_id = serializers.CharField(required = False, max_length = 20)
    voice_id = serializers.CharField(required = False, max_length = 20)
    gpt_model = serializers.ChoiceField(required = False, choices = ["gpt-3.5-turbo", "gpt-4"], default = "gpt-4")
    images = serializers.ChoiceField(required = False, choices = ["AI", "webscrap", False], default = "webscrap")
    avatar_selection = serializers.CharField(required = False, max_length = 30)
    style = serializers.ChoiceField(required = False, choices = ["vivid", "natural"], default = "vivid")
    music = serializers.CharField(required = False, max_length = 80)
    target_audience = serializers.CharField(required = False, max_length = 30)


class DownloadPlaylistSerializer(serializers.Serializer):
    link = serializers.URLField(required = True)
    category = serializers.ChoiceField(choices = ["Educational", "Gaming", "Advertisement", "Story", "Other"])


class SceneUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(required = True, max_length = 2000)
