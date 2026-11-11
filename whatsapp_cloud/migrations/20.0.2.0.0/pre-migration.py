def migrate(cr, version):
    """Meta sends again the notifications it thinks were not received: remove the copies of
    the received messages before the uniqueness of the WhatsApp IDs."""
    cr.execute("""
        DELETE FROM whatsapp_message message
         USING whatsapp_message original
         WHERE message.wa_message_id IS NOT NULL
           AND message.wa_message_id = original.wa_message_id
           AND message.account_id = original.account_id
           AND message.id > original.id
    """)
