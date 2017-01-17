# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def onchange_template_id(
            self, template_id, partner=False, fiscal_position_id=False,
            pricelist_id=False):
        """
        Este es un fix horrible a la fea implementación de odoo de este método
        que hace que no se pueda heredar
        """
        res = super(SaleOrder, self).onchange_template_id(
            template_id, partner=partner,
            fiscal_position_id=fiscal_position_id, pricelist_id=pricelist_id)
        data = res.get('value', {})
        order_line = data.get('order_line', [])
        new_order_line = []
        for line in order_line:
            if len(line) == 3:
                False, False, line_vals = line
                fpos = self.env['account.fiscal.position'].browse(
                    fiscal_position_id)
                product = self.env['product.product'].browse(
                    line_vals['product_id'])
                company_id = self.company_id or self._context.get(
                    'company_id')
                taxes = product.taxes_id.filtered(lambda r: (
                    not r.company_id or r.company_id.id == company_id))
                taxes = fpos.map_tax(taxes) if fpos else taxes
                line_vals['tax_id'] = [(6, 0, taxes.ids)]
                new_order_line.append((0, 0, line_vals))
            else:
                new_order_line.append(line)
        data['order_line'] = new_order_line
        return res
