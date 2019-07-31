##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    # this is tu fix when you are on a child company on an invoice linked to
    # a PO of the parent company
    purchase_id = fields.Many2one(
        related_sudo=True,
    )
