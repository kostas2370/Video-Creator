from celery import shared_task

from .characters import generate_reference


@shared_task(ignore_result=True, soft_time_limit=540, time_limit=600)
def generate_character_reference_task(reference_id, job_id=None, brief=None):
    generate_reference(reference_id, job_id=job_id, brief=brief)
