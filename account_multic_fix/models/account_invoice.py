##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.onchange('company_id')
    def _onchange_company(self):
        # get first journal for new company

        # si viene un default journal y no es de la misma cia que la actual
        # limpiamos el default
        default_journal_id = self.env.context.get('default_journal_id')
        if default_journal_id and self.company_id and self.env[
                'account.journal'].browse(
                    default_journal_id).company_id != self.company_id:
            default_journal_id = False
            # self = self.with_context(default_journal_id=False)

        self.journal_id = self.with_context(
            company_id=self.company_id.id,
            default_journal_id=default_journal_id,
            # necesitamos mandar type para que default elija correctamente
            type=self.type,
        )._default_journal()

        price_security_installed = False
        if 'invoice_line_tax_ids_readonly' in self.invoice_line_ids._fields:
            price_security_installed = True
        # update lines
        for line in self.invoice_line_ids:
            # we force cache update of company_id value on invoice lines
            # this fix right tax choose
            # prevent price and name being overwrited
            price_unit = line.price_unit
            name = line.name
            line.company_id = self.company_id
            line._onchange_product_id()
            if price_security_installed:
                line.invoice_line_tax_ids_readonly = line.invoice_line_tax_ids
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

    @api.constrains('fiscal_position_id', 'company_id')
    def _check_fiscal_position_company(self):
        position_company = self.fiscal_position_id.company_id
        if position_company and position_company != self.company_id:
            raise ValidationError(_(
                'The company of the invoice and from the fiscal position must'
                ' be the same!'))

    # TODO. this should go in a PR to ODOO
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        delivery_partner_id = self.get_delivery_partner_id()
        fiscal_position = self.env[
            'account.fiscal.position'].with_context(
                force_company=self.company_id.id).get_fiscal_position(
                self.partner_id.id, delivery_id=delivery_partner_id)
        if fiscal_position:
            self.fiscal_position_id = fiscal_position
        return res
