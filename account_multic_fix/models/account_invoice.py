# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _default_journal(self):
        context = self._context
        change_company = context.get('change_company')
        default_journal_id = context.get('default_journal_id')
        # if we come, for eg, from journal dashboard and we came company
        # we need to remove the defauly key
        if change_company and default_journal_id:
            context = context.copy()
            context.pop('default_journal_id')
            self = self.with_context(context)

        # TODO borrar o arreglar, al final este fix lo hicimos en
        # sale_mutlic_fix porque nos rompia el comportamiento para generar
        # factura  usando boton de dashboard contable en una tarjeta de otra
        # cia diferente a la del usuario
        # Fix that, if for eg, we came from a sale order of company a and we
        # can also se company b journals, odoo could select a journal of b
        # active_model = context.get('active_model')
        # active_id = context.get('active_id')
        # company_id = context.get(
        #     'company_id', context.get('default_company_id'))
        # if active_model and active_id and not company_id and \
        #         not default_journal_id:
        #     model = self.env[active_model]
        #     if 'company_id' in model._fields:
        #         company = model.browse(active_id).company_id
        #         if company:
        #             self = self.with_context(
        #                 company_id=model.browse(active_id).company_id.id)
        return super(AccountInvoice, self)._default_journal()

    # we need this to overwrite default
    journal_id = fields.Many2one(
        default=_default_journal
    )

    @api.model
    def _default_company(self):
        """
        Fix for eg, creation of invoice with user in company a but from a sale
        order of company b (advance invoice, normal invoice works ok)
        """
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        company_id = self._context.get('company_id')
        default_journal_id = self._context.get('default_journal_id')
        default_company_id = self._context.get('default_company_id')
        if active_model and active_id and not company_id and \
                not default_journal_id and not default_company_id:
            model = self.env[active_model]
            if 'company_id' in model._fields:
                company = model.browse(active_id).company_id
                if company:
                    return company
        return self.env['res.company']._company_default_get('account.invoice')

    # we need this to overwrite default
    company_id = fields.Many2one(
        default=_default_company
    )

    @api.onchange('company_id')
    def _onchange_company(self):
        # get first journal for new company
        self.journal_id = self.with_context(
            company_id=self.company_id.id,
            change_company=True)._default_journal()

        # update lines
        for line in self.invoice_line_ids:
            # we force cache update of company_id value on invoice lines
            # this fix right tax choose
            # prevent price and name being overwrited
            price_unit = line.price_unit
            name = line.name
            line.company_id = self.company_id
            line._onchange_product_id()
            line.name = name
            line.price_unit = price_unit

    @api.model
    def create(self, vals):
        """
        Fix that if we create an invoice from parent company of child company
        company must be set as the one from the journal
        """
        company_id = vals.get('company_id')
        journal_id = vals.get('journal_id')
        if journal_id and not company_id:
            vals['company_id'] = self.env['account.journal'].browse(
                journal_id).company_id.id
        return super(AccountInvoice, self).create(vals)

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
                'The company of the invoice and from the fiscal position must'
                ' be the same!'))
