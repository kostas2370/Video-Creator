from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from apps.series.models import CharacterReference, VideoSeries
from apps.videomanagement.models import MediaAsset, Scene, Video
from apps.videomanagement.services.media.references import archive_reference


class Command(BaseCommand):
    help = "Add existing character and video/series reference images to the media library."

    def handle(self, **options):
        count = 0
        for model in (CharacterReference, VideoSeries, Video):
            for instance in model.objects.all().select_related("created_by").iterator():
                if archive_reference(instance):
                    count += 1
        # Earlier failed jobs could leave paid images without a scene link.
        # Preserve those in the owner's library without guessing which shot they belong to.
        for video in Video.objects.exclude(dir_name="").select_related("created_by").iterator():
            if not video.created_by_id:
                continue
            directory = (Path(video.dir_name) / "images").resolve()
            if not directory.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not directory.is_dir():
                continue
            for image in directory.iterdir():
                if (image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}
                        or not image.is_file() or image.is_symlink()):
                    continue
                with image.open("rb") as source:
                    MediaAsset.from_visual(
                        user=video.created_by, upload=File(source, name=image.name),
                        title=f"{video.title} · Saved image", tags=["recovered image"],
                        kind=MediaAsset.Kind.IMAGE, source_video=video,
                    )
                count += 1
        for instance in Scene.all_objects.exclude(overlay_logo="").select_related("video__created_by").iterator():
            if archive_reference(instance):
                count += 1
        self.stdout.write(f"Archived {count} reference images (identical files reuse existing assets).")
