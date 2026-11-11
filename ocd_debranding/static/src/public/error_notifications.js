import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// The pages of the website: the session that expired, without the name of Odoo
const sessionExpired = {
    title: _t("Session expired"),
    message: _t("Your session expired. The page is about to be refreshed."),
    buttons: [
        {
            text: _t("Ok"),
            click: () => window.location.reload(true),
            close: true,
        },
    ],
};
const notifications = registry.category("error_notifications");
for (const name of ["odoo.http.session.SessionExpiredException", "werkzeug.exceptions.Forbidden"]) {
    notifications.add(name, sessionExpired, { force: true });
}
