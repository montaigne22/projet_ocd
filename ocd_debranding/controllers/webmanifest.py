from odoo.addons.web.controllers.webmanifest import WebManifest

ICON = "/ocd_debranding/static/img/ocd-icon-{size}.png"


class OcdWebManifest(WebManifest):
    """The app installed from the browser (« Install the app ») shows OCD Live: its icon and its
    colours, not those of Odoo."""

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        manifest["background_color"] = "#FFFFFF"
        manifest["theme_color"] = "#15130F"
        # The mark keeps a margin: the phones that cut the icon in a circle keep all of it
        manifest["icons"] = [
            {"src": ICON.format(size=size), "sizes": f"{size}x{size}", "type": "image/png", "purpose": purpose}
            for size in (192, 512)
            for purpose in ("any", "maskable")
        ]
        return manifest

    def _icon_path(self):
        # Offline page and icon of the shortcuts without their own icon
        return "ocd_debranding/static/img/ocd-icon-192.png"
