##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
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
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(
            order, so_line, amount)
        # este es el metodo que odoo usa en sale pero mas corrrecto seria
        # usar el get_journal
        invoice.journal_id = self.env['account.invoice'].default_get(
            ['journal_id'])['journal_id']
        return invoice
