"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers
from django.contrib.auth import authenticate
from datetime import datetime
from dateutil import relativedelta
from .utils import conds


class RegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('username', 'password', "email", "first_name", "last_name")
        extra_kwargs = {'password': {'write_only': True}, 'is_verified': {'read_only': True}}

    def validate(self, attrs):

        password = attrs.get("password")

        if relativedelta.relativedelta(datetime.now(), attrs.get("date_of_birth")).years < 18:

            raise AuthenticationFailed("You must be over 18")

        if not conds(password):
            raise AuthenticationFailed("Your password must contain at least 8 chars ,uppercase ,lowercase ,digit")

        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = "__all__"


class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only = True)
    password = serializers.CharField(write_only = True)
    tokens = serializers.DictField(read_only = True)

    class Meta:
        model = get_user_model()
        fields = ("username", "password", "tokens")

    def validate(self, attrs):
        request = self.context['request']
        username = attrs.get("username", '')
        password = attrs.get("password", '')
        auser = authenticate(username = username, password = password, request=request)
        if not auser:
            raise AuthenticationFailed("There is not a user with that credentials")
        if not auser.is_verified:
            raise AuthenticationFailed("You have to verify your account to be able to have access to your account")
        return {
            "tokens": auser.get_tokens()
        }


class VerifySerializer(serializers.Serializer):
    email = serializers.CharField(required = False, read_only = True, max_length = 100)

