"""The parcels already delivered get their amounts kept by OCD Live frozen (commission, delivery
fees), as the parcels delivered from now on: « money received » of the dashboard adds them up in the
database instead of computing each parcel at each opening."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    parcels = env["stock.picking"].search([
        ("ocd_is_parcel", "=", True), ("ocd_stage", "=", "delivered"), ("ocd_kept_frozen", "=", False),
    ])
    for start in range(0, len(parcels), 500):
        batch = parcels[start:start + 500]
        batch._ocd_freeze_kept()
        env.flush_all()
        env.invalidate_all()
