from . import controllers, models


def post_init_hook(env):
    """The sites already sent by a CDN send the clips by it too."""
    env["website"].search([("cdn_activated", "=", True)])._ocd_add_clip_cdn_filter()
