##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.one
    @api.constrains('company_id')
    def check_company(self):
        if self.company_id.consolidation_company:
            raise Warning(
                'You can not create entries on a consolidtion company')
