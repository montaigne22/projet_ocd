{
    "name": "Files On An S3 Storage (Cloudflare R2, AWS S3, Backblaze B2, MinIO)",
    "summary": "The files of Odoo copied on an S3 bucket and read from it: give the keys, the files already "
    "there are sent by themselves",
    "description": """
Files on an S3 storage
======================

The files of Odoo (photos, videos, PDF, attachments) are kept on an S3 bucket:
Cloudflare R2, AWS S3, Backblaze B2, Wasabi, MinIO or any S3 storage.

- Settings › General Settings › Files on an S3 storage: the provider, the
  bucket and its keys (or in the configuration file of the server), « Test
  the connection », then on.
- Each new file is copied on the bucket just after it is saved, checked
  (size and MD5), and tried again later when the network cuts. The files
  already there are sent in the background, a little at a time, with their
  progress on the settings.
- Odoo keeps working as before on the disk of the server: a file missing on
  the disk (another server, a new server, a disk lost) is taken back from
  the bucket when it is read. The copy on the server can stay (the safest),
  or the server keeps only the files read lately (a size in GB).
- A file deleted in Odoo is deleted on the bucket a day later; « Bring the
  files back on this server » before leaving the bucket.
- One bucket for several databases and several servers: a folder per database.
""",
    "version": "20.0.1.0.0",
    "category": "Hidden/Tools",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "external_dependencies": {"python": ["boto3"]},
    "data": [
        "security/ir.access.csv",
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
