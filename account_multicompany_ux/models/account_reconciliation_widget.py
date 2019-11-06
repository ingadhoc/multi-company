from odoo import models


class AccountReconciliation(models.AbstractModel):

    _inherit = 'account.reconciliation.widget'

    def _get_statement_line(self, st_line):
        """ Force company to use the one in the st_line and not the current company """
        res = super()._get_statement_line(st_line)
        if not st_line.partner_id:
            return res

        company_id = st_line.company_id.id
        partner = st_line.partner_id.with_context(force_company=company_id)
        if res.get('amount') > 0:
            res['open_balance_account_id'] = partner.property_account_receivable_id.id
        else:
            res['open_balance_account_id'] = partner.property_account_payable_id.id
        return res
