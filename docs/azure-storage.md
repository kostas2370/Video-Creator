# Azure media copy: first migration stage

Azure Blob Storage is currently a **copy destination**, not the active application
storage. Configuring it does not change playback, rendering, file URLs, database
references, or the local files. No database migration is required for this stage.

## Create the destination

In the Azure portal:

1. Select the intended subscription and create a resource group for Viddie.
2. Create a general-purpose v2 storage account with Standard performance. Choose
   the region near the rendering workers and choose redundancy according to your
   recovery requirements. Start with the Hot access tier for active media.
3. Require HTTPS, minimum TLS 1.2, and disable anonymous blob access. Prefer
   Microsoft Entra authentication; account keys are not needed by this command.
4. Create a container such as `viddie-media` with anonymous access set to Private.
5. Enable blob/container soft delete and blob versioning. Choose retention for
   deleted files and old versions deliberately: they continue to consume storage.
6. Give the identity running the command Storage Blob Data Contributor access
   scoped to this container. Role assignments may take time to propagate.

The command checks container access and refuses a publicly accessible container.
It does not create resources, grant roles, or change Azure security configuration.
Storage, upload/download operations, and transfers may incur Azure charges.

## Configure the copy process

Add the non-secret destination settings to `backend/.env`:

```dotenv
AZURE_STORAGE_ACCOUNT_URL=https://YOUR_ACCOUNT.blob.core.windows.net
AZURE_STORAGE_CONTAINER=viddie-media
```

Authentication uses `DefaultAzureCredential`: managed identity on supported Azure
hosts, an existing Azure CLI login on a developer machine, or Azure Identity
environment credentials. The identity must be available **inside the process or
container running the command**; a host CLI login is not automatically inherited
by Docker. Keep any service-principal credentials in the deployment secret store
and never paste them into chat, commit them, or include them in the account URL.

Azure is an optional alternative to the preferred [Cloudflare R2 destination](r2-storage.md).
Its libraries are not included in the default backend build. Install them in the
Python environment running this command, or include them in your custom image:

```sh
python -m pip install -r requirements/azure.txt
```

Run that command from `backend/` using the application's Python environment.
For Docker, rebuild the backend image before using the new command and recreate
the API container to load the updated environment configuration.

## Inventory, copy, and resume

Back up the database and local storage first. Stop generation, uploads, editing,
publishing, and cleanup while taking a consistent database/media snapshot. The
copy command detects many concurrent local writes but is not a snapshot mechanism.

From `backend/`, inspect the registered source files without connecting to Azure:

```sh
python manage.py copy_media_to_azure
```

Or with the existing Compose installation:

```sh
docker compose exec video_creator python manage.py copy_media_to_azure
```

Missing files or unsafe paths produce a nonzero exit status. The dry run checks
local paths only; it does not prove Azure authentication or upload permissions.

After reviewing the inventory, explicitly start the network copy:

```sh
docker compose exec video_creator python manage.py copy_media_to_azure --execute
```

The command reads nonempty FileField/ImageField references from video management,
series, clips, and publishing models, including records exposed by their base
managers. Duplicate references in the same storage namespace are copied once.
It never recursively scans `MEDIA_ROOT`: that directory currently includes backend
source and secrets. Unregistered intermediate files, caches, model weights,
database files, and secrets are not copied. This is **not a complete server backup**.

Local relative file names are preserved beneath separate blob prefixes:

| Local storage | Azure blob name |
| --- | --- |
| Default media | `media/<original relative name>` |
| Private clips | `clips/<original relative name>` |
| Private publishing snapshots | `publishing/<original relative name>` |

For example, a default file named `media/output/example.mp4` becomes
`media/media/output/example.mp4`. The first component identifies the storage
namespace and prevents collisions between otherwise identical relative names.
Legacy absolute database paths are converted to relative blob names only when
they are inside the file field's declared storage root. Database values stay as
saved. Absolute paths outside that root and symlinked media are rejected.

Each uploaded file is downloaded again and checked against the local SHA-256 and
size. Existing blobs are also verified byte for byte, never overwritten. Rerunning
resumes at file boundaries; an interrupted large file may need to upload again.
Verification adds download traffic and may incur transfer charges, particularly
when the copy process runs outside Azure. Conflicting files fail verification and
need operator review; no automatic delete or overwrite option is provided.

Errors identify the file's ordinal position and storage namespace, without printing
SDK responses, signed URLs, or credentials. Keep the source snapshot stable when
investigating errors so those positions remain useful. The command exits nonzero
if any file fails and retains all local originals and database references.

## Remaining work before switching active storage

Do not delete local media after this copy. A zero-failure result verifies registered
file copies only. New and edited files still live locally, and deletions are not
synchronized to Azure. Rerun while the source is idle before any future cutover;
changed files at an existing blob name require explicit conflict resolution.

Before Azure can become the active store, implement and verify:

- worker input downloads and temporary local rendering workspaces;
- uploads of newly generated media and exports;
- owner-authorized media downloads, including seeking/range behavior;
- private clip/publishing access and immutable publishing snapshots;
- restore tooling and end-to-end playback, captions, rendering, and publishing;
- a final consistent transfer, database reference changes if needed, and rollback.

Database backups, the field encryption key, and any other required server state
need a separate backup/restore plan. Keep account credentials outside media backups.

References: [Azure Python quickstart](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python),
[Azure data protection](https://learn.microsoft.com/en-gb/azure/storage/blobs/data-protection-overview).
