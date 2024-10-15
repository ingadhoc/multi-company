from odoo import models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    @api.model_create_multi
    def create(self, val_list):
        force_company = self.env.context.get('force_company_id')
        if force_company:
            if isinstance(val_list, list):
                for vals in val_list:
                    vals['company_id'] = force_company
            else:
                val_list['company_id'] = force_company
        return super().create(val_list)
