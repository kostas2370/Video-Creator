"""Azure destination for the optional media copy command."""

import mimetypes
from urllib.parse import urlparse

from apps.common.media_archive import (
    ArchiveError as ArchiveError,
    blob_name as blob_name,
    copy_verified as copy_verified,
    local_path as local_path,
    relative_name as relative_name,
)


class AzureArchive:
    def __init__(self, account_url, container):
        parsed = urlparse(account_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ArchiveError(
                "AZURE_STORAGE_ACCOUNT_URL must be an HTTPS account origin."
            )
        if not container:
            raise ArchiveError(
                "Set AZURE_STORAGE_CONTAINER to an existing private container."
            )
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ArchiveError(
                "Install requirements/azure.txt before copying to Azure."
            ) from None
        self.credential = DefaultAzureCredential()
        self.service = BlobServiceClient(account_url, credential=self.credential)
        self.container = self.service.get_container_client(container)
        try:
            properties = self.container.get_container_properties()
            if properties.get("public_access"):
                raise ArchiveError("Azure container must have public access disabled.")
        except Exception:
            self.close()
            raise

    def upload_if_missing(self, name, source, size, digest):
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import ContentSettings

        try:
            self.container.get_blob_client(name).upload_blob(
                source,
                length=size,
                overwrite=False,
                metadata={"sha256": digest},
                content_settings=ContentSettings(
                    content_type=mimetypes.guess_type(name)[0]
                    or "application/octet-stream"
                ),
            )
            return True
        except ResourceExistsError:
            return False

    def chunks(self, name):
        from azure.core import MatchConditions

        blob = self.container.get_blob_client(name)
        properties = blob.get_blob_properties()
        return blob.download_blob(
            etag=properties.etag, match_condition=MatchConditions.IfNotModified
        ).chunks()

    def close(self):
        self.service.close()
        self.credential.close()
