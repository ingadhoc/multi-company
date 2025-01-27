##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _sale_get_order_company_fix(self):
        vals = {}
        if self.company_id != self.env.user.company_id:
            vals["company_id"] = self.env.user.company_id.id
        return vals
