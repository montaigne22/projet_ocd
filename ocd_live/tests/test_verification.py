from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveVerification(OcdLiveCommon):
    """Board of the checks of the team (BoVerification)."""

    def test_check_links_and_vendors(self):
        now = fields.Datetime.now()
        listing = self.env["ocd.directory.listing"].create({
            "partner_id": self.vendor.id,
            "url": "https://www.tiktok.com/@brendawax/live",
            "state": "to_check",
            "window_start": now - timedelta(hours=1),
            "window_end": now + timedelta(hours=2),
        })
        newcomer = self.env["res.partner"].create({
            "name": "Yao Vaisselle", "ocd_is_vendor": True, "ocd_vendor_state": "to_check", "phone": "+228 90000099",
        })
        Verification = self.env["ocd.live.verification"]
        data = Verification.get_verification_data()
        columns = {column["key"]: column for column in data["columns"]}
        self.assertIn(f"link_{listing.id}", [item["key"] for item in columns["link"]["items"]])
        self.assertIn(f"vendor_{newcomer.id}", [item["key"] for item in columns["vendor"]["items"]])
        self.assertTrue(columns["done"]["done"])
        # The link is shown, the vendor is refused with a reason of the vendors
        Verification.ocd_approve("link", listing.id, {})
        self.assertEqual(listing.state, "published")
        with self.assertRaises(UserError):
            Verification.ocd_refuse("vendor", newcomer.id, False)
        reason = self.env.ref("ocd_live.refuse_reason_vendor_unreachable")
        Verification.ocd_refuse("vendor", newcomer.id, reason.id)
        self.assertEqual(newcomer.ocd_vendor_state, "refused")
        self.assertTrue(newcomer.ocd_vendor_checked_at)
        history = Verification.get_verification_data()["columns"][-1]["items"]
        self.assertEqual(len(history), 2)
        self.assertEqual({row["ok"] for row in history}, {True, False})

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(UserError):
            self.env["ocd.live.verification"].ocd_approve("payment", 1, {})
