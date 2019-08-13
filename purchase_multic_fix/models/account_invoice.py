##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
# flake8: noqa
# pylint: disable=pointless-string-statement
from odoo import api
from odoo.addons.purchase.models.account_invoice import AccountInvoice


@api.multi
def new_write(self, vals):
    result = True
    for invoice in self:
        inv = invoice.sudo()
        purchase_old = inv.invoice_line_ids.mapped('purchase_line_id.order_id')
        result = result and super(AccountInvoice, invoice).write(vals)
        purchase_new = inv.invoice_line_ids.mapped('purchase_line_id.order_id')
        #To get all po reference when updating invoice line or adding purchase order reference from vendor bill.
        purchase = (purchase_old | purchase_new) - (purchase_old & purchase_new)
        if purchase:
            message = _("This vendor bill has been modified from: %s") % (",".join(["<a href=# data-oe-model=purchase.order data-oe-id="+str(order.id)+">"+order.name+"</a>" for order in purchase]))
            invoice.message_post(body=message)
    return result
AccountInvoice.write = new_write
