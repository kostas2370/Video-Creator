import pathlib

from django.core.management import BaseCommand

from apps.videomanagement.services.media.downloads import download_video

from ...models import Intro, Outro


class Command(BaseCommand):
    help = "Setup the files you need like folders intros, outros etc"

    def handle(self, *args, **options):
        pathlib.Path("media/videos").mkdir(parents=True, exist_ok=True)
        try:
            if not Intro.objects.filter(name="basicintro").count():
                intro = download_video(
                    "https://www.youtube.com/watch?v=fQaEv_odk0w", "media/other/intros/"
                )
                Intro.objects.create(name="basicintro", file=intro)

            if not Outro.objects.filter(name="basicoutro").count():
                outro = download_video(
                    "https://www.youtube.com/watch?v=YqB62GjZqC0", "media/other/outros/"
                )
                Outro.objects.create(name="basicoutro", file=outro)

        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"An error occurred: {exc}"))

        self.stdout.write(self.style.SUCCESS("Setup is done!"))
