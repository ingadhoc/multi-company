##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    analytic_account_id = fields.Many2one(
        check_company=False,  # Unrequired company
    )
