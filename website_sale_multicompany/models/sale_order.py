##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    # Quito el check company porque durante la creacion si el cliente tiene una cuenta analitica de otra
    # company que la del website no puedo crear la orden
    # https://github.com/odoo/odoo/blob/17.0/addons/sale/models/sale_order.py#L249
    # (viene igual de 14.0 y no se toco aun en master)
    analytic_account_id = fields.Many2one(
        check_company=False,  # Unrequired company
    )

    def _sale_get_order_company_fix(self):
        vals = {}
        if self.company_id != self.env.user.company_id:
            vals['company_id'] = self.env.user.company_id.id
        return vals
