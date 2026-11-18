"""The missing cash of the couriers becomes a debt (chantier 9): the differences counted before
were already handled by the manager (a note on the cash handed over), they are not debts now."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ocd_cash_remittance
           SET shortfall_settled = TRUE,
               shortfall_note = 'Counted before the missing cash became a debt of the courier'
         WHERE state = 'done' AND shortfall > 0 AND shortfall_settled IS NOT TRUE
        """
    )
