import { AttachmentList } from "@mail/core/common/attachment_list";

import { patch } from "@web/core/utils/patch";

import { WhatsAppAttachment } from "./whatsapp_attachment";

patch(AttachmentList, {
    components: { ...AttachmentList.components, WhatsAppAttachment },
});

patch(AttachmentList.prototype, {
    /**
     * A file of a message of a WhatsApp conversation, other than an image (shown by Odoo already):
     * shown like in WhatsApp (a small player, a video in place, a document line), not as a card.
     */
    isWhatsAppMedia(attachment) {
        return Boolean(
            this.env.message?.thread?.channel?.isWhatsApp &&
                !this.env.inComposer &&
                !this.props.isSelecting &&
                !attachment.isImage &&
                !attachment.uploading &&
                attachment.type !== "url"
        );
    },
});
