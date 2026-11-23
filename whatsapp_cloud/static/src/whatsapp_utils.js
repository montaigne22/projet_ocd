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
