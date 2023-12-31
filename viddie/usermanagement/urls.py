"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *


urlpatterns = [
    path('login/', LoginView.as_view(), name = "login"),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/register/', UserRegisterView.as_view(), name = "register"),
    path('api/email-verify/', VerifyEmail.as_view(), name = "email-verify"),
]
