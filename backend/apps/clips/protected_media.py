import asyncio
import mimetypes
import re

from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.http import content_disposition_header


async def file_chunks(field, start, length):
    with field.storage.open(field.name, "rb") as file:
        await asyncio.to_thread(file.seek, start)
        while length:
            chunk = await asyncio.to_thread(file.read, min(length, 256 * 1024))
            if not chunk:
                break
            length -= len(chunk)
            yield chunk


def media_response(request, field, *, filename=None):
    if not field or not field.storage.exists(field.name):
        raise Http404("Media is unavailable.")
    size = field.size
    start, end, partial = 0, size - 1, False
    header = request.headers.get("Range")
    if header:
        if len(header) > 100:
            return range_error(size)
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
        if not match or not any(match.groups()):
            return range_error(size)
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        elif int(last) > 0:
            start = max(0, size - int(last))
        else:
            return range_error(size)
        if start >= size or start > end:
            return range_error(size)
        partial = True
    length = max(0, end - start + 1)
    response = (
        HttpResponse()
        if request.method == "HEAD"
        else StreamingHttpResponse(file_chunks(field, start, length))
    )
    response.status_code = 206 if partial else 200
    response["Content-Type"] = (
        mimetypes.guess_type(field.name)[0] or "application/octet-stream"
    )
    response["Content-Length"] = str(length)
    response["Accept-Ranges"] = "bytes"
    if partial:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    if filename:
        response["Content-Disposition"] = content_disposition_header(True, filename)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    patch_vary_headers(response, ["Cookie", "Authorization"])
    return response


def range_error(size):
    response = HttpResponse(status=416)
    response["Content-Range"] = f"bytes */{size}"
    response["Cache-Control"] = "private, no-store"
    return response


def public_clip_media(request, path):
    raise Http404("Clip media requires authenticated access.")
