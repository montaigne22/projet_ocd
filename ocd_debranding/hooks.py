from odoo.tools import BinaryBytes, file_open

ROBOT_NAME = "OCD Live"
ODOO_ROBOT_NAME = "OdooBot"


def _icon(path):
    with file_open(path, "rb") as icon:
        return icon.read()


def post_init_hook(env):
    """The robot of the messages is named OCD Live; the websites still with the icon of Odoo
    get the one of OCD Live."""
    env.ref("base.partner_root").sudo().name = ROBOT_NAME
    odoo_icon = _icon("web/static/img/favicon.ico")
    for website in env["website"].sudo().search([]):
        if not website.favicon or bytes(website.favicon) == odoo_icon:
            website.favicon = BinaryBytes(_icon("ocd_debranding/static/img/favicon.png"), filename="favicon.png")


def uninstall_hook(env):
    robot = env.ref("base.partner_root").sudo()
    if robot.name == ROBOT_NAME:
        robot.name = ODOO_ROBOT_NAME
