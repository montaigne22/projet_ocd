"""The files of Odoo on an S3 bucket (Cloudflare R2, AWS S3, Backblaze B2, MinIO...).

How it holds, whatever happens:

- Odoo keeps its files on the disk of the server as usual (its pages, its downloads and its
  cleaning are unchanged). Each file is also copied on the bucket, under <prefix>/<name> (the
  name of a file of Odoo is the SHA-1 of its content: the same content, the same object).
- A file is noted « to send » in the same transaction as its attachment, then sent just after
  the commit; when the network cuts, the scheduled task sends it again later (5 tries, then
  every hour). Each copy is checked: its size and its MD5 (ETag of the bucket).
- A file missing on the disk of a server (another server, a new server, a disk lost, a file the
  cache let go) is taken back from the bucket when Odoo reads it.
- The files already there when the storage is turned on are noted « to send », and sent a few
  at a time by the scheduled task, with their progress on the settings.
- The copy on the server stays by default (the safest). With « Keep on the server: the files read
  lately », the server lets go the oldest files read, already checked on the bucket, beyond a size.
- A file no longer used by any attachment is deleted from the bucket a day later (Odoo deletes it
  from the disk the same way).

The keys are the settings (Settings › General Settings), or the configuration file of the server:
attachment_s3_endpoint, attachment_s3_bucket, attachment_s3_access_key, attachment_s3_secret_key,
attachment_s3_region, attachment_s3_prefix (they win over the settings)."""
import base64
import contextlib
import hashlib
import logging
import os
import tempfile
import time
from datetime import timedelta

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.modules import module as odoo_module

_logger = logging.getLogger(__name__)

PARAM = "attachment_s3."
# The keys read in the settings, and in the configuration file (they win)
KEYS = ("active", "provider", "account", "endpoint", "region", "bucket", "access_key", "secret_key", "prefix",
        "keep_local", "cache_gb")
TRIES = 5
# A file no longer used is deleted from the bucket after this
GRACE_HOURS = 24
# The files of a run of the scheduled task (it goes on at the next run)
BATCH = 200
# The files read lately: their date on the disk is refreshed at most once a day
TOUCH_SECONDS = 86400
STATES = [("pending", "To Send"), ("synced", "On The Bucket"), ("error", "Not Sent")]


class AttachmentS3Error(Exception):
    """The bucket did not answer as expected."""


def _endpoint(config):
    if config.get("endpoint"):
        return config["endpoint"].strip().rstrip("/")
    if config.get("provider") == "r2" and config.get("account"):
        return f"https://{config['account'].strip()}.r2.cloudflarestorage.com"
    if config.get("provider") == "b2" and config.get("region"):
        return f"https://s3.{config['region'].strip()}.backblazeb2.com"
    return None  # AWS: the endpoint of the region


def _md5(path):
    digest = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest


class AttachmentS3Object(models.Model):
    _name = "attachment.s3.object"
    _description = "File On The S3 Storage"
    _log_access = False
    _order = "id"

    fname = fields.Char(string="File", required=True, index=True)
    size = fields.Integer()
    state = fields.Selection(selection=STATES, required=True, default="pending", index=True)
    tries = fields.Integer()
    error = fields.Char()
    noted_at = fields.Datetime(default=fields.Datetime.now)
    synced_at = fields.Datetime()
    next_try = fields.Datetime()

    _unique_fname = models.UniqueIndex("(fname)", "One row per file.")

    # === SETTINGS === #

    @api.model
    def _s3_config(self):
        """The settings of the storage: the configuration file wins over the settings."""
        params = self.env["ir.config_parameter"].sudo()
        config = {}
        for key in KEYS:
            value = tools.config.get(f"attachment_s3_{key}")
            config[key] = value if value not in (None, False, "") else params.get_str(PARAM + key)
        config["active"] = str(config.get("active") or "").lower() in ("1", "true", "yes", "on")
        config["region"] = config.get("region") or ("auto" if config.get("provider") == "r2" else None)
        config["prefix"] = (config.get("prefix") or self.env.cr.dbname).strip("/")
        config["keep_local"] = config.get("keep_local") or "all"
        try:
            config["cache_gb"] = max(int(config.get("cache_gb") or 20), 1)
        except ValueError:
            config["cache_gb"] = 20
        return config

    @api.model
    def _s3_ready(self, config=None):
        """Whether the bucket can be used: its keys are there (on or off)."""
        config = config or self._s3_config()
        return bool(config.get("bucket") and config.get("access_key") and config.get("secret_key"))

    @api.model
    def _s3_on(self, config=None):
        config = config or self._s3_config()
        return config["active"] and self._s3_ready(config)

    @api.model
    def _s3_client(self, config=None):
        """The client of the bucket (boto3), with the settings that R2 and the others accept."""
        config = config or self._s3_config()
        try:
            import boto3  # noqa: PLC0415 (an external dependency of the module)
            from botocore.config import Config  # noqa: PLC0415
        except ImportError as error:
            raise UserError(self.env._("The server needs boto3: pip install boto3.")) from error
        return boto3.client(
            "s3",
            endpoint_url=_endpoint(config),
            region_name=config.get("region") or None,
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"],
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 4, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
                # The checksums added by the recent versions of boto3 are refused by some S3
                # storages: only when the request needs one
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                s3={"addressing_style": "path" if config.get("provider") == "minio" else "auto"},
            ),
        )

    @api.model
    def _s3_key(self, fname, config=None):
        config = config or self._s3_config()
        return f"{config['prefix']}/{fname}"

    # === NOTED, SENT, TAKEN BACK === #

    @api.model
    def _s3_note(self, fnames):
        """Note `fnames` « to send » (in the transaction of their attachments)."""
        fnames = [fname for fname in dict.fromkeys(fnames) if fname]
        if not fnames:
            return
        self.env.cr.execute(
            """
            INSERT INTO attachment_s3_object (fname, state, tries, noted_at)
            SELECT name, 'pending', 0, now() AT TIME ZONE 'UTC' FROM unnest(%s::varchar[]) AS name
            ON CONFLICT (fname) DO UPDATE SET state = 'pending', tries = 0, next_try = NULL, noted_at = EXCLUDED.noted_at
            WHERE attachment_s3_object.state != 'synced'
            """,
            [fnames],
        )

    @api.model
    def _s3_send_after_commit(self, fnames):
        """Send `fnames` just after the commit of the transaction, in a transaction of its own;
        what fails stays « to send » for the scheduled task."""
        if odoo_module.current_test or not fnames:
            return
        registry = self.env.registry
        uid, context = self.env.uid, dict(self.env.context)

        def send():
            try:
                with registry.cursor() as cr:
                    env = api.Environment(cr, uid, context)
                    env["attachment.s3.object"].sudo()._s3_send(fnames)
            except Exception:  # noqa: BLE001 (never breaks the request: the scheduled task goes on)
                _logger.warning("S3 storage: files not sent now, sent later", exc_info=True)

        self.env.cr.postcommit.add(send)

    @api.model
    def _s3_send(self, fnames=None, deadline=None):
        """Send the files « to send » (`fnames`, else the next ones): each one is checked on the
        bucket (size and MD5); return the number sent."""
        config = self._s3_config()
        if not self._s3_on(config):
            return 0
        now = fields.Datetime.now()
        domain = [("state", "in", ("pending", "error")), "|", ("next_try", "=", False), ("next_try", "<=", now)]
        if fnames:
            domain.append(("fname", "in", list(fnames)))
        rows = self.sudo().search(domain, limit=BATCH, order="id")
        if not rows:
            return 0
        client = self._s3_client(config)
        Attachment = self.env["ir.attachment"]
        sent = 0
        for row in rows:
            if deadline and time.monotonic() > deadline:
                break
            path = Attachment._full_path(row.fname)
            try:
                if not os.path.exists(path):
                    # Not on this disk: on the bucket already (another server), or no longer used
                    if self._s3_exists(client, row.fname, config):
                        row.write({"state": "synced", "synced_at": now, "error": False})
                    else:
                        row._s3_failed(self.env._("The file is not on the disk of this server."))
                    continue
                digest = _md5(path)
                size = os.path.getsize(path)
                with open(path, "rb") as body:
                    answer = client.put_object(
                        Bucket=config["bucket"], Key=self._s3_key(row.fname, config), Body=body,
                        ContentLength=size, ContentMD5=base64.b64encode(digest.digest()).decode(),
                    )
                etag = (answer.get("ETag") or "").strip('"')
                if etag and "-" not in etag and etag != digest.hexdigest():
                    raise AttachmentS3Error(self.env._("The copy on the bucket is not the same file (MD5)."))
                head = client.head_object(Bucket=config["bucket"], Key=self._s3_key(row.fname, config))
                if int(head.get("ContentLength") or -1) != size:
                    raise AttachmentS3Error(self.env._("The copy on the bucket does not have the size of the file."))
                row.write({"state": "synced", "size": size, "synced_at": fields.Datetime.now(), "error": False,
                           "next_try": False})
                sent += 1
            except Exception as error:  # noqa: BLE001 (network, keys, bucket: noted, tried again)
                row._s3_failed(str(error)[:300])
        return sent

    def _s3_failed(self, message):
        for row in self:
            tries = row.tries + 1
            wait = timedelta(minutes=10 * tries) if tries < TRIES else timedelta(hours=1)
            row.write({"state": "error", "tries": tries, "error": message, "next_try": fields.Datetime.now() + wait})

    @api.model
    def _s3_exists(self, client, fname, config):
        try:
            client.head_object(Bucket=config["bucket"], Key=self._s3_key(fname, config))
        except Exception as error:  # noqa: BLE001
            code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    @api.model
    def _s3_fetch(self, fname):
        """Take back the file `fname` from the bucket on the disk of this server; return whether
        it is there now. Written next to it first, then moved (never a half file)."""
        config = self._s3_config()
        if not self._s3_ready(config):
            return False
        Attachment = self.env["ir.attachment"]
        path = Attachment._full_path(fname)
        if os.path.exists(path):
            return True
        try:
            client = self._s3_client(config)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".s3-", suffix=".part")
            try:
                with os.fdopen(handle, "wb") as target:
                    client.download_fileobj(config["bucket"], self._s3_key(fname, config), target)
                with contextlib.suppress(PermissionError):
                    os.chmod(temporary, 0o444)
                os.replace(temporary, path)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(temporary)
        except Exception:  # noqa: BLE001 (the file stays missing, as without the bucket)
            _logger.warning("S3 storage: file %s not taken back from the bucket", fname, exc_info=True)
            return False
        return True

    # === THE FILES ALREADY THERE, THE CLEANING === #

    @api.model
    def _s3_note_existing(self):
        """Note « to send » every file of the attachments not on the bucket yet."""
        self.env.cr.execute("""
            INSERT INTO attachment_s3_object (fname, state, tries, noted_at)
            SELECT DISTINCT store_fname, 'pending', 0, now() AT TIME ZONE 'UTC'
              FROM ir_attachment WHERE store_fname IS NOT NULL
            ON CONFLICT (fname) DO NOTHING
        """)
        return self.env.cr.rowcount

    @api.model
    def _s3_forget_unused(self):
        """The files no longer used by any attachment for a day: deleted from the bucket."""
        config = self._s3_config()
        if not self._s3_on(config):
            return 0
        self.env.cr.execute(
            """
            SELECT o.id, o.fname FROM attachment_s3_object o
             WHERE o.noted_at < %s
               AND NOT EXISTS (SELECT 1 FROM ir_attachment a WHERE a.store_fname = o.fname)
             ORDER BY o.id LIMIT 1000
            """,
            [fields.Datetime.now() - timedelta(hours=GRACE_HOURS)],
        )
        rows = self.browse([row_id for row_id, _fname in self.env.cr.fetchall()])
        if not rows:
            return 0
        synced = rows.filtered(lambda row: row.state == "synced")
        kept = self.browse()
        if synced:
            client = self._s3_client(config)
            answer = client.delete_objects(Bucket=config["bucket"], Delete={
                "Objects": [{"Key": self._s3_key(row.fname, config)} for row in synced], "Quiet": True,
            })
            failed = {item.get("Key") for item in answer.get("Errors") or []}
            kept = synced.filtered(lambda row: self._s3_key(row.fname, config) in failed)
        (rows - kept).unlink()
        return len(rows)

    @api.model
    def _s3_let_go(self, deadline=None, limit=None):
        """« Keep on the server: the files read lately »: beyond the size, the oldest files read,
        already checked on the bucket, are removed from the disk (taken back when read)."""
        config = self._s3_config()
        if not self._s3_on(config) or config["keep_local"] != "cache":
            return 0
        limit = config["cache_gb"] * 1024 ** 3 if limit is None else limit
        root = self.env["ir.attachment"]._filestore()
        files = []
        for folder in os.scandir(root) if os.path.isdir(root) else []:
            if not folder.is_dir() or len(folder.name) != 2:
                continue  # « checklist », « upload »: not files of attachments
            for entry in os.scandir(folder.path):
                with contextlib.suppress(OSError):
                    stat = entry.stat()
                    files.append((stat.st_mtime, stat.st_size, f"{folder.name}/{entry.name}", entry.path))
        total = sum(size for _mtime, size, _fname, _path in files)
        if total <= limit:
            return 0
        files.sort()
        removed = 0
        for index in range(0, len(files), 500):
            if total <= limit or (deadline and time.monotonic() > deadline):
                break
            chunk = files[index:index + 500]
            synced = set(self.sudo().search([("fname", "in", [item[2] for item in chunk]), ("state", "=", "synced")])
                         .mapped("fname"))
            for _mtime, size, fname, path in chunk:
                if total <= limit:
                    break
                if fname in synced:
                    with contextlib.suppress(OSError):
                        os.unlink(path)
                        total -= size
                        removed += 1
        return removed

    @api.model
    def _s3_bring_back(self, deadline=None):
        """« Bring the files back on this server »: every file used and missing on the disk is
        taken back from the bucket; return the number still missing."""
        Attachment = self.env["ir.attachment"]
        self.env.cr.execute("SELECT DISTINCT store_fname FROM ir_attachment WHERE store_fname IS NOT NULL")
        missing = 0
        for (fname,) in self.env.cr.fetchall():
            if os.path.exists(Attachment._full_path(fname)):
                continue
            if deadline and time.monotonic() > deadline:
                missing += 1
                continue
            if not self._s3_fetch(fname):
                missing += 1
        return missing

    # === THE SCHEDULED TASK === #

    @api.model
    def _cron_attachment_s3(self):
        """Every 10 minutes: the files to send (the new ones not sent, the ones already there),
        the cleaning of the bucket and of the cache, « Bring the files back » when asked."""
        params = self.env["ir.config_parameter"].sudo()
        deadline = time.monotonic() + 240
        if params.get_str(PARAM + "bring_back"):
            if not self._s3_bring_back(deadline):
                params.set_str(PARAM + "bring_back", False)
            return
        if not self._s3_on():
            return
        if not params.get_str(PARAM + "existing_noted"):
            self._s3_note_existing()
            params.set_str(PARAM + "existing_noted", fields.Datetime.to_string(fields.Datetime.now()))
        while time.monotonic() < deadline:
            if not self._s3_send(deadline=deadline):
                break
            if not odoo_module.current_test:
                self.env.cr.commit()
        self._s3_forget_unused()
        self._s3_let_go(deadline)

    @api.model
    def _s3_trigger(self):
        cron = self.env.ref("attachment_s3.ir_cron_attachment_s3", raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()

    @api.model
    def _s3_status(self):
        """The progress shown on the settings."""
        groups = dict(self.sudo()._read_group([], ["state"], ["__count"]))
        size = self.sudo()._read_group([("state", "=", "synced")], [], ["size:sum"])[0][0] or 0
        last = self.sudo().search([("state", "=", "error")], order="next_try desc", limit=1)
        return {
            "synced": groups.get("synced", 0),
            "pending": groups.get("pending", 0),
            "error": groups.get("error", 0),
            "size_gb": round(size / 1024 ** 3, 2),
            "last_error": last.error or "",
        }
