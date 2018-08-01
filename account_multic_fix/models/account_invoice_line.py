##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        return super(AccountInvoiceLine, self).get_invoice_line_account(
            type,
            product.with_context(force_company=company.id),
            fpos,
            company)
