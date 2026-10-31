from celery import shared_task

from .processing import process_project
from .rendering import export_clip
from .services import reap_stalled_exports


@shared_task(soft_time_limit=7140, time_limit=7200)
def process_project_task(project_id, token):
    process_project(project_id, token)


@shared_task(soft_time_limit=1140, time_limit=1200)
def export_clip_task(clip_id, token):
    export_clip(clip_id, token)


@shared_task(soft_time_limit=50, time_limit=60)
def reap_stalled_clip_exports():
    return reap_stalled_exports()
