##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
from odoo import models


class Website(models.Model):

    _inherit = 'website'
    
    def sale_get_order(self, force_create=False, update_pricelist=False):
        sale_order_sudo = super().sale_get_order(force_create, update_pricelist)
        vals = {}
        if sale_order_sudo.company_id !=  self.env.user.company_id:
            vals['company_id'] = self.env.user.company_id.id
            if hasattr(sale_order_sudo, 'warehouse_id') and sale_order_sudo.warehouse_id.company_id != self.env.user.company_id:
                vals['warehouse_id'] = (
                    self.env['ir.default'].get('sale.order', 'warehouse_id', company_id=self.env.user.company_id.id) or
                    self.env['stock.warehouse'].sudo().search([('company_id', '=', self.env.user.company_id.id)], limit=1).id
                )
        if vals:
            sale_order_sudo.write(vals)
        return sale_order_sudo
