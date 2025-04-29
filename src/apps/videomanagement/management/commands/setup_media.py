import os
import pathlib
import urllib

from django.core.management import BaseCommand

from ...models import Intro, Outro, Background
from ...utils.visual_utils import download_video


class Command(BaseCommand):
    help = "Setup the files you need like folders intros, outros etc"

    def handle(self, *args, **options):
        if not os.path.exists("media/videos/"):
            os.mkdir("media/videos")
        try:
            if not Intro.objects.filter(name="basicintro").count():
                intro = download_video(
                    "https://www.youtube.com/watch?v=fQaEv_odk0w", "media/other/intros/"
                )
                Intro.objects.create(category="OTHER", name="basicintro", file=intro)

            if not Outro.objects.filter(name="basicoutro").count():
                outro = download_video(
                    "https://www.youtube.com/watch?v=YqB62GjZqC0", "media/other/outros/"
                )
                Outro.objects.create(category="OTHER", name="basicoutro", file=outro)

            if not Background.objects.filter(name="basicbackground").count():
                pathlib.Path("media/other/backgrounds").mkdir(
                    parents=True, exist_ok=True
                )
                background_url = "https://i.ibb.co/SPz879q/back.jpg"
                urllib.request.urlretrieve(
                    background_url, "media/other/backgrounds/back.png"
                )

                Background.objects.create(
                    category="OTHER",
                    name="basicbackground",
                    file="media/other/backgrounds/back.png",
                    color="0,163,232",
                    image_pos_top=65,
                    image_pos_left=355,
                    avatar_pos_top=0,
                    avatar_pos_left=0,
                    through=6,
                )

        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"An error occurred: {exc}"))

        self.stdout.write(self.style.SUCCESS("Setup is done!"))
