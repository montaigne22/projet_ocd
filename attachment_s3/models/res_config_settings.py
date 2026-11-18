from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang

from .attachment_s3_object import PARAM

PROVIDERS = [
    ("r2", "Cloudflare R2"),
    ("aws", "AWS S3"),
    ("b2", "Backblaze B2"),
    ("minio", "MinIO"),
    ("other", "Other S3 storage"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attachment_s3_active = fields.Boolean(string="Files On An S3 Storage", config_parameter=PARAM + "active")
    attachment_s3_provider = fields.Selection(selection=PROVIDERS, string="Storage", default="r2",
                                              config_parameter=PARAM + "provider")
    attachment_s3_account = fields.Char(string="Account ID", config_parameter=PARAM + "account",
                                        help="Cloudflare R2: the Account ID (Cloudflare › R2 › Overview).")
    attachment_s3_endpoint = fields.Char(string="Endpoint", config_parameter=PARAM + "endpoint",
                                         help="Empty for Cloudflare R2 (made from the Account ID) and AWS S3.")
    attachment_s3_region = fields.Char(string="Region", config_parameter=PARAM + "region",
                                       help="« auto » for Cloudflare R2; e.g. eu-west-3 for AWS S3.")
    attachment_s3_bucket = fields.Char(string="Bucket", config_parameter=PARAM + "bucket")
    attachment_s3_access_key = fields.Char(string="Access Key ID", config_parameter=PARAM + "access_key")
    attachment_s3_secret_key = fields.Char(string="Secret Access Key", config_parameter=PARAM + "secret_key")
    attachment_s3_prefix = fields.Char(string="Folder", config_parameter=PARAM + "prefix",
                                       help="The folder of this database in the bucket. Empty: the name of the database.")
    attachment_s3_keep_local = fields.Selection(
        selection=[("all", "All the files (the safest)"), ("cache", "The files read lately")],
        string="Keep On The Server", default="all", config_parameter=PARAM + "keep_local",
        help="The files stay on the disk of the server too, or only the files read lately up to a size: "
        "the others are taken back from the bucket when they are read.",
    )
    attachment_s3_cache_gb = fields.Integer(string="Size On The Server (GB)", default=20,
                                            config_parameter=PARAM + "cache_gb")
    attachment_s3_from_file = fields.Char(string="From The Configuration File", compute="_compute_attachment_s3_status")
    attachment_s3_status = fields.Char(string="Progress", compute="_compute_attachment_s3_status")
    attachment_s3_last_error = fields.Char(string="Last Error", compute="_compute_attachment_s3_status")

    @api.depends("attachment_s3_active")
    def _compute_attachment_s3_status(self):
        Object = self.env["attachment.s3.object"].sudo()
        status = Object._s3_status()
        from_file = [key for key in ("endpoint", "bucket", "access_key", "secret_key", "region", "prefix")
                     if tools.config.get(f"attachment_s3_{key}")]
        for settings in self:
            settings.attachment_s3_from_file = self.env._(
                "Given by the configuration file of the server (they win): %s.", ", ".join(from_file)
            ) if from_file else False
            settings.attachment_s3_status = self.env._(
                "%(synced)s files on the bucket (%(size)s GB) · %(pending)s to send · %(error)s not sent yet",
                synced=formatLang(self.env, status["synced"], digits=0), size=formatLang(self.env, status["size_gb"], digits=1),
                pending=formatLang(self.env, status["pending"], digits=0), error=formatLang(self.env, status["error"], digits=0),
            )
            settings.attachment_s3_last_error = status["last_error"] or False

    def set_values(self):
        was_on = self.env["attachment.s3.object"].sudo()._s3_on()
        super().set_values()
        Object = self.env["attachment.s3.object"].sudo()
        if Object._s3_on() and not was_on:
            # Turned on: the files already there are noted « to send » by the scheduled task
            self.env["ir.config_parameter"].sudo().set_str(PARAM + "existing_noted", False)
            Object._s3_trigger()

    def action_attachment_s3_test(self):
        """« Test the connection »: a small file written, read and deleted on the bucket."""
        self.ensure_one()
        self.set_values()
        Object = self.env["attachment.s3.object"].sudo()
        config = Object._s3_config()
        if not Object._s3_ready(config):
            raise UserError(self.env._("Give the bucket and its two keys first."))
        key = Object._s3_key("odoo-connection-test.txt", config)
        try:
            client = Object._s3_client(config)
            client.put_object(Bucket=config["bucket"], Key=key, Body=b"Odoo")
            if client.get_object(Bucket=config["bucket"], Key=key)["Body"].read() != b"Odoo":
                raise UserError(self.env._("The file read back is not the one written."))
            client.delete_object(Bucket=config["bucket"], Key=key)
        except UserError:
            raise
        except Exception as error:  # noqa: BLE001 (the message of the storage, for the administrator)
            raise UserError(self.env._("The bucket does not answer: %s", error)) from error
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "success", "message": self.env._("The bucket answers: a file was written, read and deleted.")},
        }

    def action_attachment_s3_send_all(self):
        """« Send the files now »: every file not on the bucket yet is noted, the task starts."""
        self.ensure_one()
        Object = self.env["attachment.s3.object"].sudo()
        if not Object._s3_on():
            raise UserError(self.env._("Turn on « Files on an S3 storage » and save first."))
        count = Object._s3_note_existing()
        Object._s3_trigger()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "info", "message": self.env._(
                "%s files noted to send: they leave a little at a time, the progress shows here.", count)},
        }

    def action_attachment_s3_bring_back(self):
        """« Bring the files back on this server » (before leaving the bucket)."""
        self.ensure_one()
        Object = self.env["attachment.s3.object"].sudo()
        if not Object._s3_ready():
            raise UserError(self.env._("Give the bucket and its two keys first."))
        self.env["ir.config_parameter"].sudo().set_str(PARAM + "bring_back", "1")
        Object._s3_trigger()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "info", "message": self.env._(
                "The files missing on this server are taken back from the bucket by the scheduled task.")},
        }
