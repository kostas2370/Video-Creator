"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


from .views import TemplatePromptView, GenerateView, VideoView, AvatarView, VoiceView, SceneView, SceneImageView,\
    change_image_scene
from rest_framework import routers
from django.urls import path
from .views import download_playlist, render_video, setup, video_regenerate
router = routers.DefaultRouter()
router.register('templates', TemplatePromptView)
router.register('generate', GenerateView)
router.register('video', VideoView)
router.register('avatars', AvatarView)
router.register('voices', VoiceView)
router.register('scene', SceneView)
router.register('scene_image', SceneImageView)

urlpatterns = [path('downloadplaylist/', download_playlist),
               path('render/', render_video),
               path('change_image/', change_image_scene),
               path('setup/', setup),
               path('regenerate/', video_regenerate)
               ]


urlpatterns += router.urls
