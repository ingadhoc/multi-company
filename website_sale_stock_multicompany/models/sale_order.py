##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    def _sale_get_order_company_fix(self):
        vals = super()._sale_get_order_company_fix()
        if self.warehouse_id.company_id != self.env.user.company_id:
            vals['warehouse_id'] = self.website_id.with_context(company_fix=self.env.user.company_id.id
                                                                )._get_warehouse_available()
        return vals

    def _get_warehouse_available(self):
        self.ensure_one()
        warehouse = super()._get_warehouse_available()
        if warehouse:
            warehouse_id = self.env['stock.warehouse'].browse(warehouse)
            if warehouse_id.company_id != self.company_id:
                warehouse = self.website_id.with_context(company_fix=self.env.user.company_id.id
                                                         )._get_warehouse_available()

        return warehouse
