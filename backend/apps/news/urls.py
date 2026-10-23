from django.urls import path

from .views import NewsUpdateListView

urlpatterns = [path("", NewsUpdateListView.as_view(), name="news-list")]
