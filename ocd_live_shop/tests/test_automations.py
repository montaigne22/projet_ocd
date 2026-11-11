from odoo.tests import tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdShopAutomations(OcdShopCommon):

    def test_runs_of_the_parcels(self):
        order = self._order(self.estelle, [(self.butter, 1), (self.dress, 1)])
        automation = self.env.ref("ocd_live_shop.automation_parcel_split")
        count, last, label = automation._ocd_runs()
        self.assertGreaterEqual(count, 2, "One parcel per vendor")
        self.assertTrue(last)
        self.assertIn(order.picking_ids.sorted("create_date")[-1].name.split("/")[0], label)
        page = self.env["ocd.automation"].get_automations_page()
        groups = [group["key"] for group in page["groups"]]
        self.assertIn("shop", groups)
        self.assertIn("money", groups)
