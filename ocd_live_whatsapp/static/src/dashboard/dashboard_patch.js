import { OcdLiveDashboard } from "@ocd_live/dashboard/dashboard";
import { signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/**
 * The figures of the WhatsApp conversations on the dashboard (whatsapp_cloud computes them): the
 * first answer, the customers waiting, the time to resolve, each agent, the templates paid each
 * month; over 7 or 30 days.
 */
patch(OcdLiveDashboard.prototype, {
    setup() {
        super.setup(...arguments);
        this.whatsappBusy = signal(false);
    },

    async setWhatsappDays(days) {
        const data = this.data();
        if (!data?.whatsapp || data.whatsapp.days === days || this.whatsappBusy()) {
            return;
        }
        this.whatsappBusy.set(true);
        try {
            const whatsapp = await this.orm.call("ocd.live.dashboard", "get_whatsapp_stats", [days]);
            this.data.set({ ...this.data(), whatsapp });
        } finally {
            this.whatsappBusy.set(false);
        }
    },

    whatsappPeriodLabel(days) {
        return _t("%s days", days);
    },

    whatsappTemplatesLabel(row) {
        return _t("%(month)s: %(sent)s templates sent, %(paid)s paid", {
            month: row.label,
            sent: row.sent,
            paid: row.paid,
        });
    },
});
