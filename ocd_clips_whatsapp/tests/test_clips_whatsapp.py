from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.ocd_clips import clip_video
from odoo.addons.ocd_clips.tests.common import OcdClipsCommon, make_video
from odoo.addons.ocd_clips.tests.test_clips import fake_make
from odoo.addons.whatsapp_cloud.tests.common import REQUEST, mock_response


@tagged("post_install", "-at_install")
class TestOcdClipsWhatsapp(OcdClipsCommon):
    """The clips on WhatsApp (chantier 8, design ClipsAutomatiques): the vendor told once per live
    that its clips are ready, and the clip itself sent when they ask for it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110048", "waba_id": "2220048", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cls.brenda.write({"phone": "+237 690000048", "lang": "en_US", "ocd_whatsapp_optin": True})
        cls.Message = cls.env["whatsapp.message"]

    def _messages(self, name):
        return self.Message.search([("template_id.template_name", "=", name)], order="id")

    def _clips(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        self._moment(live, self.scarf, 30)
        with patch.object(clip_video, "make", fake_make):
            self._send(live, make_video(50))
            self._run_cron()
        return live

    def test_the_vendor_is_told_once_that_the_clips_are_ready(self):
        live = self._clips()
        ready = self._messages("ocd_clips_prets")
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready.res_id, live.id)
        day = live.ocd_clip_ids[:1]._ocd_live_day()
        self.assertIn(f"Hello, the clips of your live of {day} are ready. Clips to share: 2.", ready.body)
        template = self.env.ref("ocd_clips_whatsapp.template_clips_ready")
        path = template._render(template.button_url_value, live)[live.id]
        self.assertEqual(path, f"ocd/espace/{self.brenda._ocd_get_space_token()}/clips?live={live.id}")
        live.ocd_clip_ids.action_ocd_remake()
        with patch.object(clip_video, "make", fake_make):
            self._run_cron()
        self.assertEqual(len(self._messages("ocd_clips_prets")), 1, "Once per live")
        # Paused by the team: nothing leaves
        self.env.ref("ocd_clips.automation_clips_ready").enabled = False
        other = self._clips()
        self.assertTrue(other.ocd_clips_told_at)
        self.assertEqual(len(self._messages("ocd_clips_prets")), 1)

    def test_the_clip_sent_with_its_video(self):
        live = self._clips()
        clip = live.ocd_clip_ids.filtered(lambda clip: clip.product_tmpl_id == self.dress.product_tmpl_id)
        self.assertTrue(clip._ocd_whatsapp_ready())
        self.company.ocd_clip_whatsapp_per_day = 1
        self.assertTrue(clip._ocd_send_to_vendor())
        self.assertFalse(clip._ocd_send_to_vendor(), "1 a day at most (setting)")
        message = self._messages("ocd_clip_video")
        self.assertEqual(len(message), 1)
        self.assertIn(f"Your clip Robe en wax of the live of {clip._ocd_live_day()} is ready", message.body)
        self.assertIn(f"Its link: {clip._ocd_link_text()}, to paste in your caption.", message.body)
        answers = [mock_response({"id": "media-48"}), mock_response({"messages": [{"id": "wamid.48"}]})]
        with patch(REQUEST, side_effect=answers) as request:
            message._send()
        upload, send = request.call_args_list
        self.assertEqual(upload.kwargs["data"]["type"], "video/mp4")
        self.assertEqual(bytes(upload.kwargs["files"]["file"][1]), clip.video.content, "The video of the clip")
        header = send.kwargs["json"]["template"]["components"][0]
        self.assertEqual(header["parameters"], [{"type": "video", "video": {"id": "media-48"}}])
        self.assertEqual(message.state, "sent")
        # Refused by Meta: no button
        self.env.ref("ocd_clips_whatsapp.template_clip_video").status = "rejected"
        self.assertFalse(clip._ocd_whatsapp_ready())

    def test_the_page_of_the_clip_offers_whatsapp(self):
        live = self._clips()
        clip = live.ocd_clip_ids[:1]
        self.assertTrue(clip._ocd_whatsapp_ready())
        self.brenda.phone = False
        self.assertFalse(clip._ocd_whatsapp_ready(), "No number, no WhatsApp")
