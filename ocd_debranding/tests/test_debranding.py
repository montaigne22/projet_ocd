from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestOcdDebranding(HttpCase):
    """What the team, the vendors and the customers see never says Odoo."""

    def test_public_pages(self):
        for path in ("/web/login", "/shop", "/contactus"):
            response = self.url_open(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.text
            self.assertNotIn("Powered by", html, path)
            self.assertNotIn("odoo.com", html, path)
            self.assertNotIn('name="generator"', html, path)

    def test_back_office_page(self):
        self.authenticate("admin", "admin")
        html = self.url_open("/odoo").text
        self.assertIn("<title>OCD Live</title>", html)
        self.assertIn("/ocd_debranding/static/img/favicon.png", html)

    def test_mail_layouts(self):
        """The layouts of the e-mails, as Odoo assembles them: no Powered by Odoo, the link to
        stop following kept; the light one rendered."""
        for xmlid in ("mail.mail_notification_light", "mail.mail_notification_layout", "digest.digest_mail_main",
                      "digest.digest_section_mobile"):
            arch = self.env.ref(xmlid)._get_combined_arch()
            from lxml import etree

            text = etree.tostring(arch, encoding="unicode")
            if xmlid == "digest.digest_section_mobile":
                self.assertIn('t-if="False"', text, "The banner of Odoo Mobile is never shown")
                continue
            self.assertNotIn("odoo.com", text, xmlid)
            if xmlid.startswith("mail."):
                self.assertIn("/mail/unfollow", text, xmlid)
        values = {
            "company": self.env.company, "show_footer": True, "show_unfollow": True,
            "message": self.env["mail.message"], "record_name": "S00042", "subtitles": [],
            "lang": "en_US", "model_description": "Order", "body": "<p>Hello</p>",
        }
        html = str(self.env["ir.qweb"]._render("mail.mail_notification_light", values, minimal_qcontext=True))
        self.assertNotIn("Powered by", html)
        self.assertIn("/mail/unfollow", html)

    def test_robot(self):
        self.assertEqual(self.env.ref("base.partner_root").name, "OCD Live")
        user = new_test_user(self.env, login="ocd_new_team_member", groups="base.group_user")
        user._on_webclient_bootstrap()
        self.assertEqual(user.odoobot_state, "disabled", "No welcome chat that presents Odoo")
        chat = self.env["discuss.channel"].search([
            ("channel_type", "=", "chat"), ("channel_member_ids.partner_id", "=", user.partner_id.id),
        ])
        self.assertFalse(chat)
