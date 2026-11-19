from django.conf import settings

from apps.common.r2_archive import R2Archive
from apps.videomanagement.management.commands.copy_media_to_azure import (
    Command as CopyCommand,
)


class Command(CopyCommand):
    help = "Copy registered local media to Cloudflare R2. Dry run unless --execute is supplied."
    destination_label = "Cloudflare R2"

    def get_archive(self):
        return R2Archive(
            settings.R2_ACCOUNT_ID,
            settings.R2_BUCKET_NAME,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_JURISDICTION,
        )
