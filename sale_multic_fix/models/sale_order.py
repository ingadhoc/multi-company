##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    fiscal_position_id = fields.Many2one(
        domain="['|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]"
    )

    @api.constrains('fiscal_position_id', 'company_id')
    def _check_fiscal_position_company(self):
        position_company = self.fiscal_position_id.company_id
        if position_company and position_company != self.company_id:
            raise ValidationError(_(
                'The company of the sale order and from the fiscal position '
                'must be the same!'))

    # we add company_id to onchange
    @api.onchange('partner_shipping_id', 'partner_id', 'company_id')
    def onchange_partner_shipping_id(self):
        return super(SaleOrder, self.with_context(
            force_company=self.company_id.id)).onchange_partner_shipping_id()

    @api.multi
    def _prepare_invoice(self):
        """
        Arreglos para que se tomen cuentas de compania hija si estamos parados
        en una cia padre.
        Agregamos la opcion de force para que otros modulos puedan forzar
        usar una compania diferente
        """
        company_id = self._context.get('force_company', self.company_id.id)
        res = super(SaleOrder, self.with_context(
            company_id=company_id,
            force_company=company_id))._prepare_invoice()
        res['company_id'] = company_id
        if self.env['account.fiscal.position'].browse(
                res['fiscal_position_id']).company_id != company_id:
            res['fiscal_position_id'] = self.with_context(
                force_company=company_id).partner_invoice_id\
                .property_account_position_id.id
        return res
