##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # this is tu fix when you are on a child company and you change state of an
    # invoice linked to a PO of parent company (validate it, set as paid, etc)
    qty_invoiced = fields.Float(
        compute_sudo=True,
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        company_id = self._context.get('company_id', False)
        if not company_id:
            return res
        fpos = self.order_id.fiscal_position_id
        self.taxes_id = fpos.map_tax(
            self.product_id.supplier_taxes_id.filtered(
                lambda r: r.company_id.id == company_id))

        return res
