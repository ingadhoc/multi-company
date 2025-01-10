##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    reversed_entry_id = fields.Many2one(check_company=False)
    company_id = fields.Many2one(tracking=True)
