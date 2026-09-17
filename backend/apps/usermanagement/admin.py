from django.contrib import admin

from .models import User, Login

admin.site.register(User)
admin.site.register(Login)
