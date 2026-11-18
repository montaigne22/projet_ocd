import contextlib
import os
import time

from odoo import api, models

from .attachment_s3_object import TOUCH_SECONDS


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _file_write(self, fname, bin_value):
        """Saved on the disk as usual, then noted « to send » and sent to the bucket just after
        the commit (attachment_s3_object)."""
        super()._file_write(fname, bin_value)
        Object = self.env["attachment.s3.object"].sudo()
        if Object._s3_on():
            Object._s3_note([fname])
            Object._s3_send_after_commit([fname])

    def _s3_ensure_local(self):
        """The file of the attachment on the disk of this server: taken back from the bucket when
        it is missing; its date refreshed when the server keeps only the files read lately."""
        Object = self.env["attachment.s3.object"].sudo()
        for attachment in self:
            fname = attachment.store_fname
            if not fname:
                continue
            path = self._full_path(fname)
            if os.path.exists(path):
                with contextlib.suppress(OSError):
                    if time.time() - os.path.getmtime(path) > TOUCH_SECONDS and Object._s3_config()["keep_local"] == "cache":
                        os.utime(path)
                continue
            Object._s3_fetch(fname)

    def _file_read(self):
        self._s3_ensure_local()
        return super()._file_read()

    def _to_http_stream(self):
        """The pages and the downloads read the file on the disk: it is there first."""
        self._s3_ensure_local()
        return super()._to_http_stream()
