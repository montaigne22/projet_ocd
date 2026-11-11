def migrate(cr, version):
    """Templates synchronised before the link buttons were read from Meta: the ones with a
    link button variable keep sending it, until the next synchronisation reads the button."""
    cr.execute("""
        UPDATE whatsapp_template
           SET button_url_dynamic = TRUE
         WHERE COALESCE(button_url_value, '') != ''
    """)
