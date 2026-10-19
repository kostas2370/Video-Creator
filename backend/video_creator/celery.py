from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import before_task_publish, setup_logging

from .observability import propagate_request_id


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "video_creator.settings")


app = Celery("video_creator")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


# Carry an API failure reference through tasks and nested task publication.
before_task_publish.connect(propagate_request_id)


@setup_logging.connect
def configure_worker_logging(**kwargs):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)
