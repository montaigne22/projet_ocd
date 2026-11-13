import base64
import functools
import math

from markupsafe import Markup

from odoo import fields, models
from odoo.tools import consteq
from odoo.tools.misc import file_open, hmac

from .. import announce_image, tools

try:
    from odoo.addons.base_report_wkhtmltox.models.ir_actions_report import _wkhtml
except ImportError:  # another PDF engine
    _wkhtml = None

# Fonts of the PDF, in the ticket itself: the PDF engine needs no access to the website for them
TICKET_FONTS = {
    "OcdDisplay": "BricolageGrotesque-ExtraBold",
    "OcdText": "Figtree-Regular",
    "OcdTextSemi": "Figtree-SemiBold",
    "OcdTextBold": "Figtree-Bold",
    "OcdTextExtra": "Figtree-ExtraBold",
}


@functools.cache
def _file_base64(path):
    with file_open(path, "rb") as file:
        return base64.b64encode(file.read()).decode()


class OcdLiveBooking(models.Model):
    """The ticket of a live, and its announcement.

    The ticket is personal: a PDF for the vendor (download, WhatsApp), never shared. Its QR
    code opens the check of the team, signed by the database: a ticket changed by hand, or the
    one of a live moved since, is refused; the team lets the vendor in once, a copy shown again
    is seen at once. The seal printed is the start of this signature, and the lines of the
    background and the micro text are drawn from it: each ticket has its own.

    The announcement is an image without personal information (no number, no ticket): the
    vendor shares it with friends to say when the live is."""

    _inherit = "ocd.live.booking"

    ticket_checked_in = fields.Datetime(string="Entered At", readonly=True, copy=False)
    ticket_checked_in_by = fields.Many2one(
        comodel_name="res.users", string="Let In By", readonly=True, copy=False
    )

    # === TICKET === #

    def _ocd_ticket_signature(self):
        """Secret of the ticket: the vendor, the day and the hour of the live are in it."""
        self.ensure_one()
        message = ":".join(map(str, [
            self.id, self.partner_id.id, self.ticket_code, fields.Datetime.to_string(self.start_datetime),
        ]))
        return hmac(self.env(su=True), "ocd_live.ticket", message)[:32]

    def _ocd_ticket_check(self, signature):
        """Whether `signature` is the one of this ticket (in constant time)."""
        self.ensure_one()
        return bool(signature) and consteq(self._ocd_ticket_signature(), signature)

    def _ocd_ticket_seal(self):
        """Seal printed on the ticket, checked by eye: "7F3A-9C21"."""
        code = self._ocd_ticket_signature()[:8].upper()
        return f"{code[:4]}-{code[4:]}"

    def _ocd_ticket_check_path(self):
        self.ensure_one()
        return f"/ocd/ticket/verifier/{self.id}/{self._ocd_ticket_signature()}"

    def _ocd_ticket_qr(self):
        """QR code of the check of the ticket, for the page and the PDF."""
        return tools.qr_data_uri(f"{self.get_base_url()}{self._ocd_ticket_check_path()}")

    def _ocd_ticket_pattern(self, width=900, height=700, count=20):
        """Security lines of the background of the ticket, drawn from its signature."""
        seed = bytes.fromhex(self._ocd_ticket_signature())
        lines = []
        for index in range(count):
            amplitude = 6 + seed[index % 16] % 14
            period = 90 + seed[(index + 5) % 16] % 150
            phase = seed[(index + 9) % 16] / 255 * 2 * math.pi
            base = 16 + index * (height - 32) / (count - 1)
            points = " ".join(
                f"{x},{base + amplitude * math.sin(2 * math.pi * x / period + phase):.1f}"
                for x in range(0, width + 1, 9)
            )
            lines.append(f'<polyline points="{points}" fill="none" stroke="#F3E3D2" stroke-width="1.3"/>')
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">{"".join(lines)}</svg>'
        )
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    def _ocd_ticket_package(self):
        """The package of the live, and what waits at the studio (shelf, rack, table)."""
        self.ensure_one()
        env = self.env
        needs = {
            "shelf": env._("a shelf waits for you at the studio"),
            "rack": env._("a clothes rack waits for you at the studio"),
            "table": env._("a table waits for you at the studio"),
        }
        need = needs.get(self.studio_need) if self.mode == "studio" else False
        return self.product_id.name or "", need or ""

    def _ocd_tz_for(self, tz_name=None):
        """Time zone of the hours of the ticket: `tz_name` (the phone of the vendor on the
        page), else the one given by the context (PDF), else the vendor's."""
        self.ensure_one()
        return (
            tools.valid_tz(tz_name)
            or tools.valid_tz(self.env.context.get("ocd_tz"))
            or self.partner_id._ocd_tz_name()
        )

    def _ocd_studio_hours_line(self, tz_name):
        """For a live at the studio seen from another time zone: its hours at the studio
        ("10:00 – 11:30 at the studio (Togo Time)"), else an empty text."""
        self.ensure_one()
        company = self.company_id
        studio_tz = company.ocd_studio_tz or "Africa/Lome"
        if self.mode != "studio" or tools.same_offset(tz_name, studio_tz, self.start_datetime):
            return ""
        return self.env._(
            "%(start)s – %(end)s at the studio (%(zone)s)",
            start=f"{company._ocd_to_local(self.start_datetime):%H:%M}",
            end=f"{company._ocd_to_local(self.end_datetime):%H:%M}",
            zone=tools.zone_text(self.env, studio_tz),
        )

    def _ocd_ticket_values(self, tz_name=None):
        """What the ticket says, in the language of the environment and in the time zone of the
        vendor: the same lines on the page and in the PDF."""
        self.ensure_one()
        env = self.env
        company = self.company_id
        tz_name = self._ocd_tz_for(tz_name)
        local = tools.to_tz(self.start_datetime, tz_name)
        end = tools.to_tz(self.end_datetime, tz_name)
        city = company.ocd_studio_city or "Lomé"
        studio = self.mode == "studio"
        name = self.partner_id.name or ""
        package, need = self._ocd_ticket_package()
        seal = self._ocd_ticket_seal()
        qr = self._ocd_ticket_qr()
        if env.context.get("whatsapp_sample"):
            # The sample of the template seen by Meta: no data of a real vendor
            name, seal = env._("Your name"), "0000-0000"
            qr = tools.qr_data_uri(f"{self.get_base_url()}/ocd")
        return {
            "title": env._("Live at the studio") if studio else env._("Remote live"),
            "vendor": name,
            "name_size": 15 if len(name) <= 22 else 12.5 if len(name) <= 34 else 11,
            "category": "" if env.context.get("whatsapp_sample") else self.partner_id.ocd_category_id.name or "",
            "day": tools.day_text(env, local.date(), "EEEE d MMMM y", capital=True),
            "hours": f"{local:%H:%M} – {end:%H:%M}",
            "time_zone": tools.zone_text(env, tz_name),
            "studio_hours": self._ocd_studio_hours_line(tz_name),
            "place": env._("Studio OCD, %s", city) if studio else env._("From home, remote"),
            "package": package,
            "need": need,
            "code": self.ticket_code,
            "reference": "LIVE/0000" if env.context.get("whatsapp_sample") else self.name,
            "seal": seal,
            "check_line": env._("Scanned at the entry of the studio") if studio else env._("Checked by the team"),
            "notice": env._(
                "Personal ticket, for you only: do not share it. The team checks it at the entry; "
                "a copy is refused once the ticket is used."
            ),
            "issued": env._("Issued on %s", tools.day_text(env, fields.Date.context_today(self), "d MMMM y")),
            "micro": f" OCD LIVE · {self.ticket_code} · {seal} ·" * 14,
            "qr": qr,
            "pattern": self._ocd_ticket_pattern(),
        }

    def _ocd_ticket_css(self):
        """Fonts of the PDF, written in it."""
        faces = "".join(
            "@font-face { font-family: '%s'; src: url(data:font/truetype;base64,%s) format('truetype'); }"
            % (family, _file_base64(f"ocd_live/static/fonts/{file}.ttf"))
            for family, file in TICKET_FONTS.items()
        )
        return Markup(faces)

    def _ocd_ticket_zoom(self):
        """Zoom of the PDF: wkhtmltopdf built on an unpatched Qt prints the millimetres at 77 %
        of their size, 1.3 gives them back; its patched build and the other engines need none."""
        report = self.env.ref("ocd_live.action_report_ticket").sudo()
        if self.env["ir.actions.report"]._get_pdf_engine(report) != "wkhtmltopdf" or not _wkhtml:
            return 1
        return 1 if _wkhtml().is_patched_qt else 1.3

    def _ocd_ticket_logo(self):
        return "data:image/png;base64," + _file_base64("ocd_live/static/img/ocd_logo_round.png")

    def _ocd_ticket_pdf(self, lang=None, tz_name=None):
        """The PDF of the ticket and its file name, in `lang` and `tz_name` (else the language
        and the time zone of the vendor)."""
        self.ensure_one()
        lang = lang or self.partner_id.lang or self.env.lang
        report = self.env.ref("ocd_live.action_report_ticket").sudo().with_context(
            lang=lang, ocd_tz=self._ocd_tz_for(tz_name)
        )
        pdf, _report_type = report._render_qweb_pdf(report.report_name, self.ids)
        return pdf, f"Ticket {self.ticket_code}.pdf"

    def _ocd_let_in(self):
        """The team lets the vendor in: the ticket is used, a second scan says when and who.
        Return False when it was already used."""
        self.ensure_one()
        if self.ticket_checked_in:
            return False
        self.sudo().write({"ticket_checked_in": fields.Datetime.now(), "ticket_checked_in_by": self.env.uid})
        self.sudo().message_post(body=self.env._("Ticket checked at the entry by %s.", self.env.user.name))
        return True

    def _ocd_ticket_changed(self):
        """The ticket of a confirmed live changed (live moved): its former QR code is refused
        from now on. Extended by ocd_live_whatsapp, that sends the new ticket."""
        return False

    # === ANNOUNCEMENT === #

    def _ocd_public_path(self):
        """Public page of this live (without the first "/"), the link of its announcement:
        before the live its day and its hour, during it « Watch », after it its replay. The
        country of the vendor is in the path: without the number, the lives of the country."""
        self.ensure_one()
        code = (self.partner_id.country_id.code or "").lower()
        return f"lives/{code}/{self.id}" if len(code) == 2 else self.partner_id._ocd_public_path()

    def _ocd_announce_values(self, tz_name=None):
        """What the image of the announcement says: the public name of the vendor, its
        category, the day and the hour of the live in the time zone of the vendor, the page
        where to find it. Nothing personal: no phone number, no ticket, no reference."""
        self.ensure_one()
        env = self.env
        vendor = self.partner_id
        tz_name = self._ocd_tz_for(tz_name)
        local = tools.to_tz(self.start_datetime, tz_name)
        url = f"{self.get_base_url()}/{self._ocd_public_path()}"
        day = tools.day_text(env, local.date(), "EEEE d MMMM", capital=True)
        return {
            "headline": env._("I go live on OCD Live"),
            "name": vendor.name,
            "category": " · ".join(part for part in (vendor.ocd_category_id.name, vendor.ocd_business) if part),
            "day": day,
            "hour": f"{local:%H:%M}",
            "time_zone": tools.zone_text(env, tz_name),
            "cta": env._("Join me live"),
            "link": url.split("://", 1)[-1],
            "url": url,
            "share_text": env._(
                "I go live on OCD Live on %(day)s at %(hour)s. Join me: %(url)s",
                day=tools.day_text(env, local.date(), "EEEE d MMMM"), hour=f"{local:%H:%M}", url=url,
            ),
            "file_name": env._("OCD Live - %s.png", day),
        }

    def _ocd_announce_png(self, tz_name=None):
        """The image that announces the live, in the language of the environment (PNG)."""
        self.ensure_one()
        return announce_image.render(self._ocd_announce_values(tz_name))
