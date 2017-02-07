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
        return super(SaleOrder, self.with_context(
            company_id=self.company_id.id))._prepare_invoice()
