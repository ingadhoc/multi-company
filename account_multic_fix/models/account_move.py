##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self._origin.company_id and self.company_id != self._origin.company_id:

            # self = self.with_context(force_company=self.company_id.id)
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

            # si cambiamos la compania queremos actualizar cuenta bancaria, termino de pago, apuntes de deuda, etc.
            # este metodo refrezca tmb las lineas de deuda
            self._onchange_partner_id()
            # si bien onchange partner llama _recompute_dynamic_lines no manda el recompute_all_taxes, este refrezca
            # lineas de impuestos
            self._recompute_dynamic_lines(recompute_all_taxes=True)
        return super()._onchange_journal()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self._context.get('force_company'):
            self = self.with_context(force_company=self.company_id.id)
        res = super(AccountMove, self)._onchange_partner_id()
        partner_banks = self.bank_partner_id.bank_ids.filtered(lambda x: x.company_id == self.company_id)
        self.invoice_partner_bank_id = partner_banks and partner_banks[0]
        return res

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        if not self._context.get('force_company'):
            self = self.with_context(force_company=self.company_id.id)
        return super(AccountMove, self)._recompute_payment_terms_lines()
