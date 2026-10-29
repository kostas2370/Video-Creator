"""Configured extension hooks for the shared video workflow."""

from django.conf import settings
from django.utils.module_loading import import_string


def run_video_hooks(event, **kwargs):
    for path in settings.VIDEO_WORKFLOW_HOOKS.get(event, ()):
        import_string(path)(**kwargs)
