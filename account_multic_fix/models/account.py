# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.onchange('company_id')
    def _onchange_company(self):
        # get first journal for new company
        self.journal_id = self.with_context(
            company_id=self.company_id.id)._default_journal()
        # update lines
        for line in self.invoice_line_ids:
            line._onchange_product_id()


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        return super(AccountInvoiceLine, self).get_invoice_line_account(
            type,
            product.with_context(force_company=company.id),
            fpos,
            company)


# TODO ver si es necesario
# class account_move(models.Model):
#     _inherit = "account.move"

#     period_id = fields.Many2one(
#         domain="[('company_id','=',company_id), ('state', '=', 'draft')]")

#     @api.model
#     def create(self, vals):
#         """
#         Fix manual reonciliation from parent company.
#         En la linea "writeoff_move_id = move_obj.create(cr, uid, {" de move
#         line esta faltando el contexto que se peirde al llegar al create del
#         move, a su vez, y la compania no viene seteada en vals ni en contexto
#         la perdemos completamente, y terminand asignando la del usuario
#         por eso hacemos este truco que chequea si periodo y diario son de la
#         misma cia y fuerza compania de ese tipo
#         """
#         if not vals.get('company_id', False):
#             journal_id = vals.get('journal_id', False)
#             period_id = vals.get('period_id', False)
#             if journal_id and period_id:
#                 journal = self.env['account.journal'].browse(journal_id)
#                 period = self.env['account.period'].browse(period_id)
#                 if period.company_id == journal.company_id:
#                     vals['company_id'] = journal.company_id.id
#         return super(account_move, self).create(vals)
