from django.utils import timezone
from django_eventstream.renderers import SSEEventRenderer
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import JSONRenderer

from apps.videomanagement.event_stream import event_response
from apps.videomanagement.events import publish_update

from .models import ClipProject


@api_view(["GET"])
@renderer_classes([JSONRenderer, SSEEventRenderer])
def project_events(request, project_id):
    get_object_or_404(
        ClipProject.objects.filter(created_by=request.user), pk=project_id
    )
    return event_response(request, f"clips.{project_id}")


def update_jobs(rows, **changes):
    changes.setdefault("updated_at", timezone.now())
    field = "pk" if rows.model is ClipProject else "project_id"
    project_ids = set(rows.values_list(field, flat=True))
    changed = rows.update(**changes)
    if changed:
        for project_id in project_ids:
            publish_update(f"clips.{project_id}", kind="clips")
    return changed
