import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from apps.videomanagement.models import MusicCatalogTrack

TARGETS = {
    "educational": 100,
    "suspense": 100,
    "fun": 100,
    "horror": 10,
    "general": 50,
    "commercial": 30,
}
QUERIES = {
    "educational": ("educational background", "documentary ambient", "learning piano"),
    "suspense": ("suspense background", "tension cinematic", "mystery thriller"),
    "fun": ("fun upbeat", "playful happy", "comedy cheerful"),
    "horror": ("horror dark ambient", "creepy scary", "horror cinematic"),
    "general": ("background instrumental", "relaxing ambient", "acoustic background"),
    "commercial": (
        "corporate advertising",
        "business promotional",
        "uplifting corporate",
    ),
}


class DiscoveryError(Exception):
    pass


class YouTubeClient:
    def __init__(self, key):
        self.key = key

    def get(self, endpoint, **params):
        url = "https://www.googleapis.com/youtube/v3/" + endpoint
        try:
            with urlopen(
                url + "?" + urlencode({**params, "key": self.key}), timeout=30
            ) as response:
                return json.load(response)
        except HTTPError as exc:
            raise DiscoveryError(
                f"YouTube API returned HTTP {exc.code}; check your API key and quota."
            ) from None
        except (URLError, TimeoutError, ValueError):
            raise DiscoveryError(
                "Could not read the YouTube API response. Rerun to resume."
            ) from None


def duration_seconds(value):
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", value)
    if not match or not any(match.groups()):
        return 0
    return sum(
        int(number or 0) * multiplier
        for number, multiplier in zip(match.groups(), (86400, 3600, 60, 1))
    )


def discover(
    client, categories, *, pages_per_query=3, minimum=30, maximum=900, report=print
):
    for category in categories:
        count = MusicCatalogTrack.objects.filter(category=category).count()
        target = TARGETS[category]
        for query in QUERIES[category]:
            if count >= target:
                break
            token = None
            seen_tokens = set()
            for _ in range(pages_per_query):
                params = dict(
                    part="snippet",
                    type="video",
                    videoCategoryId="10",
                    videoLicense="creativeCommon",
                    maxResults=50,
                    q=f"{query} instrumental music creative commons",
                )
                if token:
                    params["pageToken"] = token
                page = client.get("search", **params)
                ids = list(
                    dict.fromkeys(
                        item.get("id", {}).get("videoId")
                        for item in page.get("items", [])
                        if item.get("id", {}).get("videoId")
                    )
                )
                videos = (
                    client.get(
                        "videos", part="snippet,contentDetails,status", id=",".join(ids)
                    )
                    if ids
                    else {}
                )
                now = datetime.now(timezone.utc).isoformat()
                for video in videos.get("items", []):
                    if count >= target:
                        break
                    if (
                        video.get("id") not in ids
                        or video.get("status", {}).get("license") != "creativeCommon"
                    ):
                        continue
                    duration = duration_seconds(
                        video.get("contentDetails", {}).get("duration", "")
                    )
                    if not minimum <= duration <= maximum:
                        continue
                    snippet = video.get("snippet", {})
                    title = snippet.get("title", "").strip()
                    if not title:
                        continue
                    tags = [category, "instrumental candidate"]
                    tags += [
                        tag.strip().lower()[:30]
                        for tag in snippet.get("tags", [])
                        if isinstance(tag, str) and tag.strip()
                    ]
                    tags = list(dict.fromkeys(tags))[:12]
                    _, created = MusicCatalogTrack.objects.get_or_create(
                        source_id=f"youtube:{video['id']}",
                        defaults={
                            "source_url": f"https://www.youtube.com/watch?v={video['id']}",
                            "title": title[:100],
                            "category": category,
                            "tags": tags,
                            "duration": duration,
                            "metadata": {
                                "category": category,
                                "youtube_id": video["id"],
                                "channel_title": snippet.get("channelTitle", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "description": snippet.get("description", ""),
                                "declared_license": "creativeCommon",
                                "discovered_at": now,
                            },
                        },
                    )
                    count += int(created)
                if count >= target:
                    break
                token = page.get("nextPageToken")
                if not token or token in seen_tokens:
                    break
                seen_tokens.add(token)
        report(f"{category}: {count}/{target} candidates")
    return {
        category: MusicCatalogTrack.objects.filter(category=category).count()
        for category in categories
    }


def export_catalog(path):
    tracks = []
    for track in MusicCatalogTrack.objects.filter(
        source_id__startswith="youtube:"
    ).order_by("category", "source_id"):
        metadata = track.metadata
        tracks.append(
            {
                "youtube_id": metadata["youtube_id"],
                "title": track.title,
                "category": track.category,
                "tags": track.tags,
                "duration": track.duration,
                "channel_title": metadata.get("channel_title", ""),
                "channel_id": metadata.get("channel_id", ""),
                "declared_license": metadata["declared_license"],
                "discovered_at": metadata["discovered_at"],
            }
        )
    Path(path).write_text(
        json.dumps(
            {"schema_version": 1, "tracks": tracks}, ensure_ascii=False, indent=2
        )
        + "\n"
    )
    return len(tracks)
