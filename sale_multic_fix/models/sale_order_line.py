##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # this is tu fix when you are on a child company and you change state of an
    # invoice linked to a SO of parent company (validate it, set as paid, etc)
    qty_invoiced = fields.Float(
        compute_sudo=True,
    )

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Arreglos para que se tomen cuentas de compania hija si estamos parados
        en una cia padre
        """
        company_id = self._context.get('force_company', self.company_id.id)
        self = self.with_context(force_company=company_id)
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        # si se fuerza una cia y es distinta a la de la sale order
        # tenemos que cambiar los impuestos, no solo vale el chequeo de forzar
        # cia porque forzamos siempre por si estamos en una padre creando para
        # hija
        if self._context.get('force_company') and \
                company_id != self.company_id.id:
            fpos = (
                self.order_id.fiscal_position_id or
                self.order_id.partner_id.property_account_position_id)
            taxes = self.product_id.taxes_id.filtered(
                lambda r: company_id == r.company_id.id)
            taxes = fpos.map_tax(taxes) if fpos else taxes
            res['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
        return res
