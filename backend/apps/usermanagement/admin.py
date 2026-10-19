from django.contrib import admin

from .models import Login, User

admin.site.register(User)
admin.site.register(Login)
