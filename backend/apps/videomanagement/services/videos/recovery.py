"""Keep running video jobs distinct from projects abandoned by a dead worker."""

import logging
from contextlib import contextmanager
from threading import Event, Thread

from django.db import close_old_connections, connections
from django.utils import timezone

from apps.videomanagement.models import Video

logger = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 60


def _refresh_heartbeat(video_id, operation_id=None):
    # QuerySet.update avoids editor refresh events for heartbeat-only writes.
    return (
        Video.objects.in_flight()
        .filter(pk=video_id, operation_id=operation_id)
        .update(updated_at=timezone.now())
    )


def _heartbeat(video_id, stopped, operation_id=None):
    try:
        while not stopped.wait(HEARTBEAT_SECONDS):
            try:
                close_old_connections()
                if not _refresh_heartbeat(video_id, operation_id):
                    return
            except Exception:
                logger.exception(
                    "Could not refresh video job heartbeat for %s", video_id
                )
            finally:
                close_old_connections()
    finally:
        # This thread owns its database connection; release it when work finishes.
        connections.close_all()


@contextmanager
def video_job_heartbeat(video_id, operation_id=None):
    """Refresh liveness even while a provider or encoder blocks the worker."""
    active = _refresh_heartbeat(video_id, operation_id)
    stopped = Event()
    thread = Thread(
        target=_heartbeat, args=(video_id, stopped, operation_id), daemon=True
    )
    if active:
        thread.start()
    try:
        yield bool(active)
    finally:
        stopped.set()
        if active:
            thread.join(timeout=2)
