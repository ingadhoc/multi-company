##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('journal_id')
    def _onchange_journal(self):
        company_changed = False
        if self._origin.company_id:
            company_changed = self.company_id != self._origin.company_id
        if self.line_ids:
            company_changed = self.company_id != self.line_ids[0].account_id.company_id
        elif self.invoice_partner_bank_id.company_id and self.invoice_partner_bank_id.company_id != self.company_id:
            company_changed = True
        elif self.invoice_payment_term_id.company_id and self.invoice_payment_term_id.company_id != self.company_id:
            company_changed = True
        elif self.fiscal_position_id.company_id and self.fiscal_position_id.company_id != self.company_id:
            company_changed = True
        if company_changed:
            # self = self.with_context(force_company=self.company_id.id)
            # si cambiamos la compania queremos actualizar cuenta bancaria, termino de pago, apuntes de deuda, etc.
            # este metodo refrezca tmb las lineas de deuda
            self._onchange_partner_id()
            # update lines
            for line in self.invoice_line_ids:
                # we force cache update of company_id value on invoice lines
                # this fix right tax choose
                # prevent price and name being overwrited
                price_unit = line.price_unit
                name = line.name
                product_uom = line.product_uom_id
                line.company_id = self.company_id
                line._onchange_product_id()
                line.name = name
                line.price_unit = price_unit
                line.product_uom_id = product_uom

                # To prevent the mixen company with account and taxes when the line doesn't have a product, 
                # we force to choose a new account after change the journal for a different company
                if not line.display_type and not line.product_id:
                    if line.account_id.company_id != line.company_id:
                        if line.move_id.is_sale_document(include_receipts=True):
                            line.account_id = line.move_id.journal_id.default_credit_account_id
                        elif line.move_id.is_purchase_document(include_receipts=True):
                            line.account_id = line.move_id.journal_id.default_debit_account_id
                    if any([line.company_id.id != l.company_id.id for l in line.tax_ids]):
                        taxes = line._get_computed_taxes()
                        if taxes and line.move_id.fiscal_position_id:
                            taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
                        line.tax_ids = taxes or [(5,0,0)]
            # we need to force change currency
            if self.currency_id != self.company_id.currency_id:
                self._onchange_currency()
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
