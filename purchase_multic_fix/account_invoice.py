# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

# al final este arreglo no fue necesario por cambios en _onchange_company
# de account_multic_fix
# @api.onchange('partner_id', 'company_id')
# def _onchange_partner_id(self):
#     """
#     En las po, la funcion action_view_invoice manda un default_journal_id
#     (en realidad lo hace mal porque se fija si hay un diario para la moneda
#     de la PO pero los diarios no suelene tener moneda, igual en una segunda
#     factura si manda como default el diario de la primera), luego odoo
#     en una modificacio de invoices en purchase, si viene default
#     journal usa ese en el onchange, pero si cambiamos de cia, no termina
#     cambiando el diario, corregimos eso.
#     """
#     default_journal_id = self.env.context.get('default_journal_id')
#     if default_journal_id:
#         if self.env['account.journal'].browse(
#                 default_journal_id).company_id != self.company_id:
#             self = self.with_context(default_journal_id=False)
#     res = super(AccountInvoice, self)._onchange_partner_id()
#     return res
