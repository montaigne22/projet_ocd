from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveSecurity(OcdLiveCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team_user = new_test_user(cls.env, login="ocd_team", groups="ocd_live.group_ocd_live_user")
        cls.manager = new_test_user(cls.env, login="ocd_manager", groups="ocd_live.group_ocd_live_manager")
        cls.portal_user = new_test_user(cls.env, login="ocd_portal", groups="base.group_portal")
        cls.employee = new_test_user(cls.env, login="ocd_employee", groups="base.group_user")

    def test_team_books_but_does_not_delete(self):
        booking = self._book(self.starts[0]).with_user(self.team_user)
        booking.mode = "remote"
        with self.assertRaises(AccessError):
            booking.unlink()

    def test_only_a_manager_confirms_without_payment(self):
        booking = self._book(self.starts[0])
        with self.assertRaises(AccessError):
            booking.with_user(self.team_user).action_confirm()
        booking.with_user(self.manager).action_confirm()
        self.assertEqual(booking.state, "confirmed")

    def test_outsiders_see_nothing(self):
        booking = self._book(self.starts[0])
        for user in (self.portal_user, self.employee):
            with self.assertRaises(AccessError):
                booking.with_user(user).read(["partner_id"])
            with self.assertRaises(AccessError):
                self.env["ocd.directory.pass"].with_user(user).search([])

    def test_space_token_is_hidden(self):
        token = self.vendor._ocd_get_space_token()
        self.assertGreaterEqual(len(token), 16)
        self.assertEqual(self.env["res.partner"]._ocd_find_by_space_token(token), self.vendor)
        # another token: the last character changed (never the same one)
        other = token[:-1] + ("y" if token.endswith("x") else "x")
        self.assertFalse(self.env["res.partner"]._ocd_find_by_space_token(other))
        self.assertFalse(self.env["res.partner"]._ocd_find_by_space_token(""))
        with self.assertRaises(AccessError):
            self.vendor.with_user(self.manager).read(["ocd_space_token"])
        self.vendor.action_ocd_reset_space_link()
        self.assertFalse(self.env["res.partner"]._ocd_find_by_space_token(token))
