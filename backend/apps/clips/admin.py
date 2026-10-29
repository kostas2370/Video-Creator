from django.contrib import admin

from .models import Clip, ClipProject

admin.site.register(ClipProject)
admin.site.register(Clip)
