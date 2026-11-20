import io
import unittest
from unittest.mock import Mock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from apps.common.media_archive import ArchiveError
from apps.common.r2_archive import R2Archive


class R2ArchiveTests(unittest.TestCase):
    def test_requires_valid_account_bucket_and_credentials(self):
        for args in (
            ("", "viddie-media", "key", "secret"),
            ("a" * 32, "invalid/bucket", "key", "secret"),
            ("a" * 32, "viddie-media", "", ""),
            ("a" * 32, "viddie-media", "key", "secret", "other"),
        ):
            with self.subTest(args=args), self.assertRaises(ArchiveError):
                R2Archive(*args)

    def test_real_sdk_accepts_conditional_single_and_multipart_requests(self):
        client = boto3.client(
            "s3",
            region_name="auto",
            endpoint_url="https://example.r2.cloudflarestorage.com",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        self.addCleanup(client.close)
        archive = R2Archive.__new__(R2Archive)
        archive.client, archive.bucket, archive.part_size = client, "viddie-media", 5
        with Stubber(client) as stub:
            stub.add_client_error(
                "head_object", service_error_code="404", http_status_code=404
            )
            stub.add_response("put_object", {"ETag": '"small"'})
            stub.add_client_error(
                "head_object", service_error_code="404", http_status_code=404
            )
            stub.add_response("create_multipart_upload", {"UploadId": "upload"})
            stub.add_response("upload_part", {"ETag": '"first"'})
            stub.add_response("upload_part", {"ETag": '"second"'})
            stub.add_response("complete_multipart_upload", {"ETag": '"large"'})
            self.assertTrue(
                archive.upload_if_missing("media/small", io.BytesIO(b"a"), 1, "hash")
            )
            self.assertTrue(
                archive.upload_if_missing(
                    "media/large", io.BytesIO(b"abcdefgh"), 8, "hash"
                )
            )
            stub.assert_no_pending_responses()


class R2SDKTests(unittest.TestCase):
    def setUp(self):
        self.client_patch = patch("boto3.client")
        self.factory = self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.client = self.factory.return_value
        self.archive = R2Archive("a" * 32, "viddie-media", "key", "secret")
        self.addCleanup(self.archive.close)

    def error(self, status):
        return ClientError(
            {
                "Error": {"Code": str(status)},
                "ResponseMetadata": {"HTTPStatusCode": status},
            },
            "request",
        )

    def missing(self):
        self.client.head_object.side_effect = self.error(404)

    def test_client_uses_r2_endpoint_and_scoped_credentials(self):
        kwargs = self.factory.call_args.kwargs
        self.assertEqual(
            kwargs["endpoint_url"], f"https://{'a' * 32}.r2.cloudflarestorage.com"
        )
        self.assertEqual(kwargs["region_name"], "auto")
        self.assertEqual(kwargs["aws_secret_access_key"], "secret")
        self.assertEqual(kwargs["config"].request_checksum_calculation, "when_required")

    def test_eu_bucket_uses_jurisdiction_endpoint(self):
        archive = R2Archive("b" * 32, "viddie-media", "key", "secret", "eu")
        self.addCleanup(archive.close)
        self.assertEqual(
            self.factory.call_args.kwargs["endpoint_url"],
            f"https://{'b' * 32}.eu.r2.cloudflarestorage.com",
        )

    def test_existing_object_is_not_uploaded(self):
        self.assertFalse(
            self.archive.upload_if_missing("media/a", io.BytesIO(b"a"), 1, "hash")
        )
        self.client.put_object.assert_not_called()

    def test_single_upload_has_atomic_no_overwrite_condition(self):
        self.missing()
        self.assertTrue(
            self.archive.upload_if_missing("media/a", io.BytesIO(b"a"), 1, "hash")
        )
        self.assertEqual(self.client.put_object.call_args.kwargs["IfNoneMatch"], "*")
        self.assertEqual(
            self.client.put_object.call_args.kwargs["StorageClass"], "STANDARD"
        )

    def test_concurrent_writer_is_verified_instead_of_overwritten(self):
        self.missing()
        self.client.put_object.side_effect = self.error(412)
        self.assertFalse(
            self.archive.upload_if_missing("media/a", io.BytesIO(b"a"), 1, "hash")
        )

    def test_permission_error_does_not_attempt_upload(self):
        self.client.head_object.side_effect = self.error(403)
        with self.assertRaises(ClientError):
            self.archive.upload_if_missing("media/a", io.BytesIO(b"a"), 1, "hash")
        self.client.put_object.assert_not_called()

    def test_multipart_commit_also_prevents_overwrites(self):
        self.missing()
        self.archive.part_size = 5
        self.client.create_multipart_upload.return_value = {"UploadId": "upload"}
        self.client.upload_part.side_effect = [{"ETag": "part1"}, {"ETag": "part2"}]
        self.assertTrue(
            self.archive.upload_if_missing(
                "media/a", io.BytesIO(b"abcdefgh"), 8, "hash"
            )
        )
        self.assertEqual(self.client.upload_part.call_count, 2)
        self.assertEqual(
            self.client.complete_multipart_upload.call_args.kwargs["IfNoneMatch"], "*"
        )
        self.client.abort_multipart_upload.assert_not_called()

    def test_multipart_failure_aborts_unfinished_upload(self):
        self.missing()
        self.archive.part_size = 5
        self.client.create_multipart_upload.return_value = {"UploadId": "upload"}
        self.client.upload_part.side_effect = RuntimeError("Disconnected")
        with self.assertRaises(RuntimeError):
            self.archive.upload_if_missing(
                "media/a", io.BytesIO(b"abcdefgh"), 8, "hash"
            )
        self.client.abort_multipart_upload.assert_called_once_with(
            Bucket="viddie-media", Key="media/a", UploadId="upload"
        )

    def test_multipart_race_aborts_and_preserves_winner(self):
        self.missing()
        self.archive.part_size = 5
        self.client.create_multipart_upload.return_value = {"UploadId": "upload"}
        self.client.upload_part.return_value = {"ETag": "part"}
        self.client.complete_multipart_upload.side_effect = self.error(412)
        self.assertFalse(
            self.archive.upload_if_missing(
                "media/a", io.BytesIO(b"abcdefgh"), 8, "hash"
            )
        )
        self.client.abort_multipart_upload.assert_called_once()

    def test_verification_download_uses_etag_and_closes_body(self):
        self.client.head_object.return_value = {"ETag": '"version"'}
        body = Mock()
        body.iter_chunks.return_value = [b"abc", b"def"]
        self.client.get_object.return_value = {"Body": body}
        self.assertEqual(list(self.archive.chunks("media/a")), [b"abc", b"def"])
        self.client.get_object.assert_called_once_with(
            Bucket="viddie-media", Key="media/a", IfMatch='"version"'
        )
        body.close.assert_called_once()

    def test_client_creation_does_not_add_a_bucket_probe_before_the_first_request(self):
        self.client.head_bucket.assert_not_called()
