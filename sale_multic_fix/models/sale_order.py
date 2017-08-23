# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    # @api.onchange('company_id')
    # def _onchange_company(self):
    #     # get first journal for new company
    #     self.journal_id = self.with_context(
    #         company_id=self.company_id.id,
    #         change_company=True)._default_journal()

    #     # update lines
    #     for line in self.invoice_line_ids:
    #         # we force cache update of company_id value on invoice lines
    #         # this fix right tax choose
    #         # prevent price and name being overwrited
    #         price_unit = line.price_unit
    #         name = line.name
    #         line.company_id = self.company_id
    #         line._onchange_product_id()
    #         line.name = name
    #         line.price_unit = price_unit

    # @api.model
    # def create(self, vals):
    #     """
    #     Fix that if we create an invoice from parent company of child company
    #     company must be set as the one from the journal
    #     """
    #     company_id = vals.get('company_id')
    #     journal_id = vals.get('journal_id')
    #     if journal_id and not company_id:
    #         vals['company_id'] = self.env['account.journal'].browse(
    #             journal_id).company_id.id
    #     return super(AccountInvoice, self).create(vals)

    fiscal_position_id = fields.Many2one(
        domain="['|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]"
    )

    @api.one
    @api.constrains('fiscal_position_id', 'company_id')
    def _check_fiscal_position_company(self):
        position_company = self.fiscal_position_id.company_id
        if position_company and position_company != self.company_id:
            raise ValidationError(_(
                'The company of the sale order and from the fiscal position '
                'must be the same!'))

    @api.multi
    # we add company_id to onchange
    @api.onchange('partner_shipping_id', 'partner_id', 'company_id')
    def onchange_partner_shipping_id(self):
        self.fiscal_position_id = self.env[
            'account.fiscal.position'].with_context(
            force_company=self.company_id.id).get_fiscal_position(
            self.partner_id.id, self.partner_shipping_id.id)
        # TODO mejorar, no se porque este no funciona
        # return super(SaleOrder, self.with_context(
        #     force_company=self.company_id.id)).onchange_partner_shipping_id()

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
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Arreglos para que se tomen cuentas de compania hija si estamos parados
        en una cia padre
        """
        company_id = self._context.get('force_company', self.company_id.id)
        self = self.with_context(force_company=company_id)
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        # si se fuerza una cia tenemos que cambiar los impuestos
        if self._context.get('force_company'):
            fpos = (
                self.order_id.fiscal_position_id or
                self.order_id.partner_id.property_account_position_id)
            taxes = self.product_id.taxes_id.filtered(
                lambda r: company_id == r.company_id.id)
            taxes = fpos.map_tax(taxes) if fpos else taxes
            res['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
        return res


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        self.ensure_one()
        order = order.with_context(
            force_company=order.company_id.id)
        self = self.with_context(
            company_id=order.company_id.id,
            default_company_id=order.company_id.id,
            force_company=order.company_id.id)
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(
            order, so_line, amount)
        # este es el metodo que odoo usa en sale pero mas corrrecto seria
        # usar el get_journal
        invoice.journal_id = self.env['account.invoice'].default_get(
            ['journal_id'])['journal_id']
        return invoice
