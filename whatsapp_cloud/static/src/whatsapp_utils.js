import { _t } from "@web/core/l10n/translation";

/** Call an action of a WhatsApp conversation, and run the window action it may return. */
export async function callWhatsappAction(store, channel, method, args = []) {
    const result = await store.env.services.orm.call("discuss.channel", method, [
        [channel.id],
        ...args,
    ]);
    if (result && typeof result === "object" && result.type) {
        await store.env.services.action.doAction(withViews(result));
    }
    return result;
}

/**
 * A window action returned by a method called directly (not by a button of a form) has no views
 * added by the server: the web client needs them. Taken from its view_mode ("form" by default).
 */
export function withViews(action) {
    if (action.type !== "ir.actions.act_window" || action.views?.length) {
        return action;
    }
    const modes = (action.view_mode || "form").split(",").map((mode) => mode.trim());
    return {
        ...action,
        views: modes.filter(Boolean).map((mode) => [false, mode === "tree" ? "list" : mode]),
    };
}

/** Minutes before the end of the 24-hour window from which the time left is shown as urgent. */
export const WINDOW_URGENT_MINUTES = 60;

/**
 * The time left to answer the customer for free (24-hour window after their last message; after
 * it, only a paid template reaches them): `null` when the window is closed, else
 * `{ minutes, urgent, text, short, tooltip, ms }`, `ms` being the time until the text changes.
 */
export function whatsappWindowLeft(validUntil) {
    const { DateTime } = luxon;
    if (!validUntil) {
        return null;
    }
    const now = DateTime.now();
    const ms = validUntil.diff(now).as("milliseconds");
    if (ms <= 0) {
        return null;
    }
    const minutes = Math.floor(ms / 60000);
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    let short;
    if (minutes < 1) {
        short = _t("less than 1 min");
    } else if (hours) {
        short = _t("%(hours)s h %(minutes)s", { hours, minutes: String(rest).padStart(2, "0") });
    } else {
        short = _t("%(minutes)s min", { minutes: rest });
    }
    const until = validUntil.hasSame(now, "day")
        ? validUntil.toLocaleString(DateTime.TIME_SIMPLE)
        : validUntil.toLocaleString({ weekday: "short", hour: "2-digit", minute: "2-digit" });
    return {
        minutes,
        urgent: minutes < WINDOW_URGENT_MINUTES,
        short,
        text: _t("%(duration)s left", { duration: short }),
        tooltip: _t("Free answers until %(time)s: after it, only a paid template reaches the customer.", {
            time: until,
        }),
        ms: ms - minutes * 60000 + 100,
    };
}
