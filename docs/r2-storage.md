# Cloudflare R2: private active media storage

R2 can serve as the active private media store. A local working cache is retained
for FFmpeg and other processing tools. First copy and verify existing registered
media, then enable `R2_STORAGE_ENABLED=true` in every API and worker environment.
No database schema migration is required; existing file references and R2 namespaces
remain compatible. Without this flag, storage remains local.

## Set up Cloudflare

1. In the Cloudflare dashboard, open **Storage & databases → R2 Object Storage**.
   Activate R2 if needed. Review the billing terms: the free allowance does not
   prevent charges above that allowance.
2. Create a bucket such as `viddie-media`, using **Standard** storage. For an
   EU-jurisdiction bucket, select the EU jurisdiction and set `R2_JURISDICTION=eu`
   below. A location hint alone is different from a jurisdiction restriction.
3. Keep the **Public Development URL disabled** and do not attach a public custom
   domain. Media and private publishing snapshots must stay private.
4. Under **Manage R2 API tokens**, create S3 credentials with **Object Read & Write**
   scoped to this bucket only. Store the access key ID and secret access key in
   the server's secret configuration. Do not use a global Cloudflare API key or
   paste credentials into chat. Secret access keys are only shown once.
5. Keep an automatic lifecycle rule to abort abandoned multipart uploads. The
   command aborts failed uploads when possible, but a terminated process cannot
   clean up its unfinished upload immediately.

The command uses the S3 API, which does not inspect Cloudflare's public development
URL or custom-domain settings. Verify privacy in the dashboard before copying.
It checks that the configured bucket is accessible and never creates buckets,
credentials, public URLs, or access policies.

## Configure the backend

Add these settings to the backend's environment or `backend/.env`:

```dotenv
R2_ACCOUNT_ID=YOUR_CLOUDFLARE_ACCOUNT_ID
R2_BUCKET_NAME=viddie-media
R2_ACCESS_KEY_ID=YOUR_BUCKET_SCOPED_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
R2_JURISDICTION=
R2_STORAGE_ENABLED=false
```

The endpoint is derived from the account ID and jurisdiction; arbitrary endpoints
are not accepted. Credentials are server-side only and never sent to the frontend.

New backend builds include the S3 client. For an existing Python environment,
install `requirements/r2.txt` from the `backend/` directory. For Docker, rebuild
the backend image and recreate the API and all Celery containers after configuring
their environment. All processes need the same R2 configuration and SDK dependency.
Do not commit `.env` or keys to version control.

## Preview the copy

From `backend/` with the existing Compose stack:

```sh
docker compose exec video_creator python manage.py copy_media_to_r2
```

This is a local-only dry run. It requires no R2 credentials and performs no network
requests. It checks registered FileField/ImageField references in video management,
series, clips, and publishing. It includes records exposed by each model's base
manager and deduplicates identical references in each storage namespace.

`MEDIA_ROOT` currently includes backend source files. The command deliberately
does not scan that directory recursively. It does not upload secrets, databases,
model weights, caches, or unregistered intermediate media. Maintain a separate
database/server backup and protect the provider-key encryption secret separately.

## Copy and verify

Back up the database and local media first. Pause uploads, generation, edits,
publishing, and cleanup for a consistent source snapshot. Then explicitly execute:

```sh
docker compose exec video_creator python manage.py copy_media_to_r2 --execute
```

Without Docker, run `python manage.py copy_media_to_r2` with the same optional
`--execute` argument in the configured backend environment.

Original names are retained under storage namespaces:

| Local storage | R2 key |
| --- | --- |
| Default media | `media/<original relative name>` |
| Private clips | `clips/<original relative name>` |
| Private publishing snapshots | `publishing/<original relative name>` |

For example, `media/output/example.mp4` in default storage is copied to
`media/media/output/example.mp4`. Legacy absolute database paths inside their
declared storage root are converted to relative keys without editing the database.
Paths outside that root, symlinks, and missing files fail validation.

Uploads use conditional writes, including at multipart completion, so an existing
object is never overwritten. Larger files use multipart upload with bounded
memory. Every copied or already-existing object is downloaded and checked against
the local SHA-256 and byte count. Downloads use an ETag condition to detect remote
changes during verification. A failed/interrupted run can be rerun: completed
files are verified again, while incomplete files restart at the file boundary.
Four files transfer concurrently by default. Use `--workers 1` for a constrained
host or choose up to `--workers 16`; the file queue and per-transfer buffers are bounded.

Verification adds read requests and transfer traffic. R2 does not charge download
bandwidth, but storage and request charges may apply; your compute host may have
its own transfer charges. Conflicting objects are reported as failures and need
manual review. This command has no overwrite or delete option.

The command reports totals and exits nonzero on failures. Errors omit credentials,
raw SDK responses, and signed URLs. **Keep the local originals**. No local or
committed R2 media is deleted by this command.

## Enable active storage

After a successful verified copy, set `R2_STORAGE_ENABLED=true` and restart the API
and every Celery worker/beat process with the rebuilt image. Keep the bucket private.

- Uploads are saved locally and uploaded to R2; the remote bytes are downloaded and
  checked before the storage operation succeeds. An R2 failure prevents a new file
  reference from being committed. A failed operation can leave an unregistered local
  or R2 copy for later review; it never removes the source.
- Model saves also publish registered files written directly by renderers/providers.
  Use `storage.save()` for file-bearing bulk/queryset updates, which bypass model
  save signals. Do not write files directly and then attach them using `QuerySet.update()`.
- Authenticated media endpoints retain ownership and signed publishing-job checks.
  They stream byte ranges from R2, including HEAD and video seeking. Local nginx
  acceleration is bypassed in R2 mode. No public bucket or browser credentials are
  needed, and browser requests remain on the application's origin.
- Accessing a missing local `.path` downloads the R2 object into the existing local
  storage root, checks SHA-256 and size, and publishes it atomically. This supports
  workers on a fresh host. Existing local processing files remain in use.
- Reusing a generated filename with different bytes creates a new object and a new
  field filename; the previous R2 object and local source are retained. Existing
  identical objects use the SHA-256 metadata from the prior verified upload.
- Storage deletion is deliberately a no-op while R2 is enabled, including automatic
  cleanup after replacing or deleting database records. Both local and remote copies
  remain. No eviction, expiry, or storage reclamation is enabled.

Rollback: disable `R2_STORAGE_ENABLED` and restart all processes. This installation
keeps local originals and new local files, so the local paths remain usable. If a
fresh host has only a partial cache, restore all referenced media before switching
back to local-only mode. Keep independent database and encryption-key backups;
R2 does not back up those.

This design moves media delivery and persistence to R2; it does not yet reduce local
disk usage. A separately verified cache-eviction policy is needed for that. Normal
writes and cache restores perform extra read requests for verification.

References: [Cloudflare S3 setup](https://developers.cloudflare.com/r2/get-started/s3/),
[Python integration](https://developers.cloudflare.com/r2/examples/aws/boto3/),
[conditional write compatibility](https://developers.cloudflare.com/r2/api/s3/api/),
[current R2 pricing](https://developers.cloudflare.com/r2/pricing/).
