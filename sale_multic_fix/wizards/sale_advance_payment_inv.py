##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    deposit_taxes_id = fields.Many2many(
        default=lambda self: self._default_deposit_taxes_id()
    )

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        """ Corregimos facturas de adelantos para dos casos:
        1. Al estar logueados en una cia pero que el pedido sea de cia hija
        2. al usar sale type con un journal de una cia hija
        En el caso de que haya posicion fiscal seteada y con compañia, la
        borramos momentaneamente porque el metodo de odoo "_create_invoice"
        no es heredable (Como el _prepare_invoice).
        """
        self.ensure_one()
        company_id = order.company_id.id
        if 'type_id' in order._fields and order.type_id.journal_id:
            company_id = order.type_id.journal_id.company_id.id

        order = order.with_context(
            force_company=company_id)
        self = self.with_context(
            company_id=company_id,
            default_company_id=company_id,
            force_company=company_id)
        original_fiscal_position_id = False
        if order.fiscal_position_id.company_id and order.\
                fiscal_position_id.company_id.id != company_id:
            original_fiscal_position_id = order.fiscal_position_id
            order.fiscal_position_id = False
        invoice = super()._create_invoice(
            order, so_line, amount)

        if original_fiscal_position_id:
            order.fiscal_position_id = original_fiscal_position_id
        invoice._onchange_company()
        invoice.compute_taxes()
        return invoice

    @api.model
    def _default_deposit_taxes_id(self):
        """ A priori esto no es necesario pero ya que luego al crear
        factura limpia impuestos segun la compania que corresponda
        Pero para sale_ux donde mostramos precio con/sin impuestos
        entonces si viene bien tenerlo bien
        """
        sale_obj = self.env['sale.order']
        order = sale_obj.browse(self._context.get('active_ids'))[0]
        return self._default_product_id().taxes_id.filtered(
            lambda r: not order.company_id or r.company_id == order.company_id)
