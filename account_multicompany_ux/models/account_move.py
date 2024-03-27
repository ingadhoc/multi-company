##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    reversed_entry_id = fields.Many2one(check_company=False)
    company_id = fields.Many2one(tracking=True)

    @api.constrains('company_id')
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(_(
                    'You can not create entries on a consolidation company'))

    @api.depends('company_id')
    def _compute_partner_bank_id(self):
        """ If company is changed the partner bank must be updated."""
        return super()._compute_partner_bank_id()

    @api.depends('partner_id', 'company_id')
    def _compute_invoice_payment_term_id(self):
        for move in self:
            # avoid changing payment term if same partner and existing payment term is suitable for current company
            if move.partner_id == move._origin.partner_id and (
                    not move.invoice_payment_term_id.company_id or move.invoice_payment_term_id.company_id == move.company_id):
                continue
            move = move.with_company(move.company_id)
            if move.is_sale_document(include_receipts=True) and move.partner_id.property_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_payment_term_id
            elif move.is_purchase_document(include_receipts=True) and move.partner_id.property_supplier_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_supplier_payment_term_id
            else:
                move.invoice_payment_term_id = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for move in self:
            if not self._origin:
                self.invoice_line_ids.company_id = self.company_id
