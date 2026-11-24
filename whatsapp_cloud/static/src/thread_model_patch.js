import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/**
 * More than 24 hours since the last message of the customer: what the team writes in the
 * conversation is an internal note (never sent: only a template reaches the customer now), with
 * its files. The commands (/note...) go as they are.
 */
patch(Thread.prototype, {
    async post(body, postData = {}, extraData = {}) {
        if (this.channel?.whatsappNoteOnly && !postData.isNote) {
            return super.post(body, { ...postData, isNote: true }, extraData);
        }
        return super.post(...arguments);
    },
});
