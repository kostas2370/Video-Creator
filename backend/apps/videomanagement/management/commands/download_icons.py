"""Download whole open icon collections into local storage and the Icon table."""

import hashlib
import json

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.videomanagement.models import Icon

COLLECTIONS = {
    "lucide": "https://raw.githubusercontent.com/lucide-icons/lucide/main/LICENSE",
    "mdi": "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/LICENSE",
}


def download(url):
    response = requests.get(url, timeout=(5, 60))
    response.raise_for_status()
    return response.content


def svg_artwork(icon, collection):
    width, height = icon.get("width", collection.get("width", 24)), icon.get("height", collection.get("height", 24))
    body = icon["body"].replace("currentColor", "#ffffff")
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 {width:g} {height:g}">{body}</svg>'.encode()


class Command(BaseCommand):
    help = "Download Lucide and Material Design Icons and populate the searchable Icon table. Artwork stays in MEDIA_ROOT, outside Git."

    def add_arguments(self, parser):
        parser.add_argument("--collections", nargs="+", choices=COLLECTIONS, default=list(COLLECTIONS))
        parser.add_argument("--limit", type=int, help="Import at most this many icons per collection.")

    def handle(self, *args, **options):
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("Limit must be positive.")
        for prefix in options["collections"]:
            try:
                data = json.loads(download(f"https://raw.githubusercontent.com/iconify/icon-sets/master/json/{prefix}.json"))
                license_text = download(COLLECTIONS[prefix])
                license_path = f"media/icons/{prefix}/LICENSE.txt"
                if not default_storage.exists(license_path):
                    default_storage.save(license_path, ContentFile(license_text))
                count = self.import_collection(prefix, data, options["limit"])
                self.stdout.write(self.style.SUCCESS(f"{prefix}: {count} icons imported."))
            except requests.RequestException as exc:
                raise CommandError(f"Could not import {prefix}: {exc}") from exc

    def import_collection(self, prefix, data, limit):
        info = data["info"]
        categories = {}
        for category, names in data.get("categories", {}).items():
            for name in names:
                categories.setdefault(name, []).append(category)
        existing = Icon.objects.filter(collection=prefix).in_bulk()
        created, updated = [], []
        for name, definition in data["icons"].items():
            if limit and len(created) + len(updated) >= limit:
                break
            if definition.get("hidden"):
                continue
            artwork = svg_artwork(definition, data)
            key = f"{prefix}:{name}"
            icon = existing.get(key) or Icon(key=key, collection=prefix)
            digest = hashlib.sha256(artwork).hexdigest()[:16]
            filename = f"media/icons/{prefix}/{name}-{digest}.svg"
            if not default_storage.exists(filename):
                filename = default_storage.save(filename, ContentFile(artwork))
            icon.name = name.replace("-", " ").title()
            icon.description = "; ".join([icon.name, *categories.get(name, [])])
            icon.file = filename
            icon.license = info["license"].get("spdx", info["license"]["title"])
            icon.license_url = info["license"].get("url", "")
            icon.attribution = info.get("author", {}).get("name", "")
            (updated if key in existing else created).append(icon)
        with transaction.atomic():
            Icon.objects.bulk_create(created, batch_size=200)
            if updated:
                Icon.objects.bulk_update(updated, ["name", "description", "file", "license", "license_url", "attribution"], batch_size=200)
        return len(created) + len(updated)
