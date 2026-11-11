/** Call an action of a WhatsApp conversation, and run the window action it may return. */
export async function callWhatsappAction(store, channel, method, args = []) {
    const result = await store.env.services.orm.call("discuss.channel", method, [
        [channel.id],
        ...args,
    ]);
    if (result && typeof result === "object" && result.type) {
        await store.env.services.action.doAction(result);
    }
    return result;
}
