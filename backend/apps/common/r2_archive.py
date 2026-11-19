"""Cloudflare R2 copy destination, using conditional writes and bounded memory."""

import mimetypes
import re

from apps.common.media_archive import ArchiveError


class R2Archive:
    part_size = 64 * 1024 * 1024

    def __init__(
        self, account_id, bucket, access_key_id, secret_access_key, jurisdiction=""
    ):
        if not re.fullmatch(r"[a-f0-9]{32}", account_id or ""):
            raise ArchiveError(
                "Set R2_ACCOUNT_ID to the Cloudflare account's 32-character ID."
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket or ""):
            raise ArchiveError("Set R2_BUCKET_NAME to an existing R2 bucket.")
        if jurisdiction not in {"", "eu", "fedramp"}:
            raise ArchiveError("R2_JURISDICTION must be blank, eu, or fedramp.")
        if not access_key_id or not secret_access_key:
            raise ArchiveError(
                "Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY in the server environment."
            )
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ArchiveError(
                "Install requirements/r2.txt before copying to R2."
            ) from None
        suffix = f".{jurisdiction}" if jurisdiction else ""
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}{suffix}.r2.cloudflarestorage.com",
            region_name="auto",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"mode": "standard", "max_attempts": 3},
                connect_timeout=10,
                read_timeout=120,
                max_pool_connections=16,
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            self.close()
            raise

    def upload_if_missing(self, name, source, size, digest):
        from botocore.exceptions import ClientError

        # Avoid re-uploading large, already copied videos on subsequent runs.
        # Conditional writes below close the race between this read and commit.
        try:
            self.client.head_object(Bucket=self.bucket, Key=name)
            return False
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                raise
        parameters = {
            "Bucket": self.bucket,
            "Key": name,
            "ContentType": mimetypes.guess_type(name)[0] or "application/octet-stream",
            "Metadata": {"sha256": digest},
            "StorageClass": "STANDARD",
        }
        upload_id = None
        try:
            if size <= self.part_size:
                self.client.put_object(
                    **parameters, Body=source, ContentLength=size, IfNoneMatch="*"
                )
            else:
                upload_id = self.client.create_multipart_upload(**parameters)[
                    "UploadId"
                ]
                parts = []
                # Increase the part size for very large videos to stay below
                # S3's 10,000-part limit, while streaming one part at a time.
                chunk_size = max(self.part_size, (size + 9998) // 9999)
                while data := source.read(chunk_size):
                    part = self.client.upload_part(
                        Bucket=self.bucket,
                        Key=name,
                        UploadId=upload_id,
                        PartNumber=len(parts) + 1,
                        Body=data,
                    )
                    parts.append({"PartNumber": len(parts) + 1, "ETag": part["ETag"]})
                self.client.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=name,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                    IfNoneMatch="*",
                )
                upload_id = None
            return True
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 412:
                # Another writer committed this key first. The shared copier
                # verifies its actual bytes rather than trusting its metadata.
                return False
            raise
        finally:
            if upload_id:
                self.client.abort_multipart_upload(
                    Bucket=self.bucket, Key=name, UploadId=upload_id
                )

    def chunks(self, name):
        properties = self.client.head_object(Bucket=self.bucket, Key=name)
        response = self.client.get_object(
            Bucket=self.bucket, Key=name, IfMatch=properties["ETag"]
        )
        body = response["Body"]
        try:
            yield from body.iter_chunks(chunk_size=4 * 1024 * 1024)
        finally:
            body.close()

    def close(self):
        self.client.close()
