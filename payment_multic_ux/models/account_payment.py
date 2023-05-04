from odoo import models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def create(self, val_list):
        force_company = self.env.context.get('force_company_id')
        if force_company:
            for vals in val_list:
                vals['company_id'] = force_company
        return super().create(val_list)