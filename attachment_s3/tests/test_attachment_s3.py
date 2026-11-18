import base64
import hashlib
import io
import os
import uuid
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.attachment_s3.models.attachment_s3_object import PARAM, AttachmentS3Object


class NotFound(Exception):
    response = {"Error": {"Code": "404"}}


class FakeBucket:
    """An S3 bucket in memory, as boto3 answers."""

    def __init__(self):
        self.objects = {}
        self.down = False

    def _check(self):
        if self.down:
            raise ConnectionError("The network is down")

    def put_object(self, Bucket, Key, Body, ContentLength=None, ContentMD5=None):  # noqa: N803 (boto3)
        self._check()
        data = Body.read() if hasattr(Body, "read") else Body
        if ContentMD5:
            assert base64.b64encode(hashlib.md5(data).digest()).decode() == ContentMD5
        self.objects[Bucket, Key] = data
        return {"ETag": f'"{hashlib.md5(data).hexdigest()}"'}

    def head_object(self, Bucket, Key):  # noqa: N803
        self._check()
        if (Bucket, Key) not in self.objects:
            raise NotFound()
        return {"ContentLength": len(self.objects[Bucket, Key])}

    def get_object(self, Bucket, Key):  # noqa: N803
        self._check()
        return {"Body": io.BytesIO(self.objects[Bucket, Key])}

    def download_fileobj(self, Bucket, Key, target):  # noqa: N803
        self._check()
        if (Bucket, Key) not in self.objects:
            raise NotFound()
        target.write(self.objects[Bucket, Key])

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop((Bucket, Key), None)

    def delete_objects(self, Bucket, Delete):  # noqa: N803
        for item in Delete["Objects"]:
            self.objects.pop((Bucket, item["Key"]), None)
        return {}


@tagged("post_install", "-at_install")
class TestAttachmentS3(TransactionCase):
    """The files of Odoo copied on an S3 bucket, checked, taken back when missing, deleted when no
    longer used; the files already there sent when the storage is turned on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bucket = FakeBucket()
        cls.patcher = patch.object(AttachmentS3Object, "_s3_client", lambda self, config=None: cls.bucket)
        cls.patcher.start()
        cls.addClassCleanup(cls.patcher.stop)
        cls.params = cls.env["ir.config_parameter"].sudo()
        for key, value in {"provider": "r2", "account": "abc123", "bucket": "odoo-files", "access_key": "key",
                           "secret_key": "secret", "prefix": "tests"}.items():
            cls.params.set_str(PARAM + key, value)
        cls.Object = cls.env["attachment.s3.object"].sudo()
        cls.Attachment = cls.env["ir.attachment"]

    def setUp(self):
        super().setUp()
        self.bucket.objects.clear()
        self.bucket.down = False
        self._turn(True)

    def _turn(self, on):
        self.params.set_str(PARAM + "active", "1" if on else False)

    def _attachment(self):
        content = f"Photo {uuid.uuid4()}".encode()
        return self.Attachment.create({"name": "photo.jpg", "raw": content}), content

    def _row(self, attachment):
        return self.Object.search([("fname", "=", attachment.store_fname)])

    def test_a_new_file_goes_to_the_bucket_checked(self):
        attachment, content = self._attachment()
        row = self._row(attachment)
        self.assertEqual(row.state, "pending", "Noted with its attachment")
        self.assertEqual(self.Object._s3_send(), 1)
        self.assertEqual(row.state, "synced")
        self.assertEqual(row.size, len(content))
        self.assertEqual(self.bucket.objects["odoo-files", f"tests/{attachment.store_fname}"], content)
        config = self.Object._s3_config()
        self.assertEqual(config["region"], "auto")
        from odoo.addons.attachment_s3.models.attachment_s3_object import _endpoint  # noqa: PLC0415

        self.assertEqual(_endpoint(config), "https://abc123.r2.cloudflarestorage.com")

    def test_the_network_cuts(self):
        attachment, _content = self._attachment()
        self.bucket.down = True
        self.Object._s3_send()
        row = self._row(attachment)
        self.assertEqual((row.state, row.tries), ("error", 1))
        self.assertTrue(row.next_try)
        self.assertIn("network", row.error)
        self.bucket.down = False
        row.next_try = False
        self.Object._s3_send()
        self.assertEqual(row.state, "synced", "Sent again later")

    def test_a_missing_file_comes_back_from_the_bucket(self):
        attachment, content = self._attachment()
        self.Object._s3_send()
        path = self.Attachment._full_path(attachment.store_fname)
        os.unlink(path)
        attachment.invalidate_recordset(["raw"])
        self.assertEqual(attachment.raw.content, content, "Read from the bucket")
        self.assertTrue(os.path.exists(path), "Kept again on the disk of the server")
        os.unlink(path)
        stream = attachment._to_http_stream()
        self.assertEqual(stream.type, "path", "The pages read it on the disk")
        # The bucket down and the file missing: empty, as without the bucket, never an error
        os.unlink(path)
        self.bucket.down = True
        attachment.invalidate_recordset(["raw"])
        self.assertFalse(attachment.raw)

    def test_the_files_already_there(self):
        self._turn(False)
        attachment, content = self._attachment()
        self.assertFalse(self._row(attachment), "Off: nothing noted")
        self._turn(True)
        self.params.set_str(PARAM + "existing_noted", False)
        self.Object._cron_attachment_s3()
        self.assertEqual(self._row(attachment).state, "synced")
        self.assertEqual(self.bucket.objects["odoo-files", f"tests/{attachment.store_fname}"], content)
        self.assertTrue(self.params.get_str(PARAM + "existing_noted"))

    def test_a_file_no_longer_used_leaves_the_bucket(self):
        attachment, _content = self._attachment()
        self.Object._s3_send()
        key = ("odoo-files", f"tests/{attachment.store_fname}")
        row = self._row(attachment)
        attachment.unlink()
        self.assertEqual(self.Object._s3_forget_unused(), 0, "A day of grace")
        self.env.cr.execute("UPDATE attachment_s3_object SET noted_at = noted_at - interval '2 days' WHERE id = %s",
                            [row.id])
        self.Object._s3_forget_unused()
        self.assertNotIn(key, self.bucket.objects)
        self.assertFalse(row.exists())

    def test_the_server_keeps_the_files_read_lately(self):
        old, content = self._attachment()
        recent, _content = self._attachment()
        not_sent, _content = self._attachment()
        self.Object._s3_send([old.store_fname, recent.store_fname])
        path = self.Attachment._full_path(old.store_fname)
        os.utime(path, (1, 1))
        self.params.set_str(PARAM + "keep_local", "cache")
        sizes = sum(os.path.getsize(self.Attachment._full_path(a.store_fname)) for a in (recent, not_sent))
        total = sum(entry.stat().st_size for folder in os.scandir(self.Attachment._filestore())
                    if folder.is_dir() and len(folder.name) == 2 for entry in os.scandir(folder.path))
        self.Object._s3_let_go(limit=total - 1)
        self.assertFalse(os.path.exists(path), "The oldest file read, on the bucket, let go")
        self.assertTrue(os.path.exists(self.Attachment._full_path(not_sent.store_fname)), "Never a file not sent")
        self.assertTrue(sizes)
        old.invalidate_recordset(["raw"])
        self.assertEqual(old.raw.content, content, "Taken back when read")

    def test_the_settings(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("files on the bucket", settings.attachment_s3_status)
        result = settings.action_attachment_s3_test()
        self.assertEqual(result["params"]["type"], "success")
        self.assertFalse(self.bucket.objects, "The test file is deleted")
        attachment, _content = self._attachment()
        path = self.Attachment._full_path(attachment.store_fname)
        self.Object._s3_send()
        os.unlink(path)
        settings.action_attachment_s3_bring_back()
        self.Object._cron_attachment_s3()
        self.assertTrue(os.path.exists(path), "Brought back on the server")
        self.assertFalse(self.params.get_str(PARAM + "bring_back"))
