import os
import tempfile
from dataclasses import dataclass

from django.core.management import BaseCommand

@dataclass(frozen=True)
class Checkpoint:
    name: str
    drive_id: str
    dest_dir: str


CHECKPOINTS = (
    # SadTalker
    Checkpoint(
        "SadTalker_V0.0.2_256.safetensors",
        "1_uAlwOrG-YTqjky3COl8n9hxdTC-brH_",
        "checkpoints",
    ),
    Checkpoint(
        "SadTalker_V0.0.2_512.safetensors",
        "14W9BTsAjb6QWjZzXNXDm125OG8_P6ROm",
        "checkpoints",
    ),
    Checkpoint("epoch_20.pth", "11mLpf5uot3tlX8hOicZwYOmonq3MgLkZ", "checkpoints"),
    Checkpoint(
        "mapping_00109-model.pth.tar",
        "1VlvjInhvPzYtjRtaBEvu2Ht_K6fmkiD5",
        "checkpoints",
    ),
    Checkpoint(
        "mapping_00229-model.pth.tar",
        "1EP3mUgVwnteWibYrMsYU9QfWPehuK5EV",
        "checkpoints",
    ),
    # pirender, which is the facerender make_avatar_video() actually asks for
    Checkpoint(
        "epoch_00190_iteration_000400000_checkpoint.pt",
        "1zduHsGBcm__QBj3E34i_THkLomaMmiyO",
        "checkpoints",
    ),
    # GFPGAN, used when a render asks for a face enhancer
    Checkpoint("GFPGANv1.4.pth", "131fX1v-GzhYS4PPJNAH3VGaEOadBBXsY", "gfpgan/weights"),
    Checkpoint(
        "alignment_WFLW_4HG.pth",
        "1vXIb5g9o5WR7N2ugL_5RNP7EO2ogvOGd",
        "gfpgan/weights",
    ),
    Checkpoint(
        "detection_Resnet50_Final.pth",
        "13InykawN1RgwTwaI1cVkbMoQI_ufuMsh",
        "gfpgan/weights",
    ),
    Checkpoint(
        "parsing_parsenet.pth", "107PDeGInnl4KzIRyubTVdz5qFsJ3C2xb", "gfpgan/weights"
    ),
)


class Command(BaseCommand):
    help = (
        "Download the SadTalker and GFPGAN checkpoints. Skips anything already "
        "present, so it is safe to run on every container start."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download even if the file is already there.",
        )
        parser.add_argument(
            "--only",
            choices=["checkpoints", "gfpgan"],
            help="Restrict to one of the two destinations.",
        )

    def handle(self, *args, **options):
        try:
            import gdown
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "gdown is not installed. It is in the requirements files; "
                    "run pip install gdown if this is a local checkout."
                )
            )
            return

        wanted = CHECKPOINTS
        if options["only"]:
            prefix = "checkpoints" if options["only"] == "checkpoints" else "gfpgan"
            wanted = tuple(c for c in wanted if c.dest_dir.startswith(prefix))

        downloaded = skipped = failed = 0

        for checkpoint in wanted:
            path = os.path.join(checkpoint.dest_dir, checkpoint.name)

            if os.path.exists(path) and not options["force"]:
                self.stdout.write(f"present, skipping: {path}")
                skipped += 1
                continue

            os.makedirs(checkpoint.dest_dir, exist_ok=True)
            self.stdout.write(f"downloading: {path}")

            handle, tmp_path = tempfile.mkstemp(
                dir=checkpoint.dest_dir, prefix=f".{checkpoint.name}.", suffix=".part"
            )
            os.close(handle)

            try:
                gdown.download(id=checkpoint.drive_id, output=tmp_path, quiet=False)
                if os.path.getsize(tmp_path) == 0:
                    raise RuntimeError("downloaded file is empty")
                os.replace(tmp_path, path)
                downloaded += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(f"failed: {checkpoint.name} -- {exc}")
                )
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        summary = f"{downloaded} downloaded, {skipped} already present, {failed} failed"

        if failed:
            self.stderr.write(
                self.style.ERROR(
                    f"{summary}. Google Drive rate-limits popular files; re-run this "
                    "command to pick up whatever is still missing."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Checkpoints ready: {summary}"))
