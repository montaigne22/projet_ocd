from . import controllers, models


def post_init_hook(env):
    """The key of the call server, created at the installation."""
    env["res.config.settings"]._whatsapp_call_get_token()
