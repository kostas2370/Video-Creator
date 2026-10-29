from celery import shared_task


@shared_task(soft_time_limit=7140, time_limit=7200)
def process_project_task(project_id, token):
    from .processing import process_project

    process_project(project_id, token)


@shared_task(soft_time_limit=1140, time_limit=1200)
def export_clip_task(clip_id, token):
    from .rendering import export_clip

    export_clip(clip_id, token)
