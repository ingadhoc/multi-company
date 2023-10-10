##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    reversed_entry_id = fields.Many2one(check_company=False)

    @api.constrains('company_id')
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(_(
                    'You can not create entries on a consolidation company'))
