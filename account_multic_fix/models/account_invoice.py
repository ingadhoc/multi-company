##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    fiscal_position_id = fields.Many2one(
        domain="['|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]"
    )

    @api.onchange('company_id')
    def _onchange_company(self):

        # odoo llama primero a este metodo antes del _onchange_partner_id,
        # entonces al hacer el cambio por interfaz no se terminan actualizando
        # los impuestos porque la fp es la de la compania anterior. Con esto
        # verificamos forzamos siempre la actualización de la fp
        if self.fiscal_position_id and \
           self.fiscal_position_id.company_id != self.company_id:
            self._onchange_partner_id()

        # get first journal for new company

        # si viene un default journal y no es de la misma cia que la actual
        # limpiamos el default
        default_journal_id = self.env.context.get('default_journal_id') or self.journal_id.id
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
        # We remove the manual tax include in the invoice because if you added
        # before change the company the tax_id are belong to the previous
        # company
        self.tax_line_ids -= self.tax_line_ids.filtered('manual')

        # we change the bank account in case if the type are out_invoice or in_refund
        if self.type in ('out_invoice', 'in_refund') and\
                self.partner_bank_id and self.company_id not in self.partner_bank_id.partner_id.ref_company_ids:
            bank_account = self._get_default_bank_id(self.type, self.company_id.id)
            self.partner_bank_id = bank_account

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
        return super().create(vals)

    @api.constrains('fiscal_position_id', 'company_id')
    def _check_fiscal_position_company(self):
        if any(self.filtered(
                lambda x: x.fiscal_position_id.company_id
                and x.fiscal_position_id.company_id != x.company_id)):
            raise ValidationError(_(
                'The company of the invoice and from the fiscal position must'
                ' be the same!'))

    # TODO. this should go in a PR to ODOO
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """ This fixes that odoo is not sending the force_company while getting
        the fiscal position (this line: https://bit.ly/2VSbLcA)
        """
        res = super(AccountInvoice, self.with_context(
            force_company=self.company_id.id))._onchange_partner_id()
        return res
