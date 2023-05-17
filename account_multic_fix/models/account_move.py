##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        # we override this method to add filter by companies in the env instead of the company of the user
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_ids = self.env.companies.ids
            domain = [('company_id', 'in', company_ids), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    @api.onchange("company_id")
    def _onchange_company(self):
        """ Similar a account_invoice_fiscal_position_update
        Este metodo es necesario para recomputar impuestos al cambiar diario que cambie
        compañía (las cuentas ya se recomputan bien solas)"""
        res = {}
        lines_without_product = self.env["account.move.line"]
        invoice_lines = self.invoice_line_ids.filtered(
            lambda l: "product" == l.display_type
        )
        for line in invoice_lines:
            if not line.product_id:
                lines_without_product |= line
            else:
                line._compute_tax_ids()
                line._compute_account_id()
        # si tiene termino de pago pero no es compatible con nueva compañia, recomputamos termino de pago
        # al recomputar el termino de pago tmb se recomputan las lineas a cobrar/pagar
        # pero si el termino de pago no se cambia, es necesario cambiar las cuentas de las lineas de pago, por eso el else
        if self.invoice_payment_term_id.company_id and self.invoice_payment_term_id.company_id != self.company_id:
            self._compute_invoice_payment_term_id()
        else:
            self.line_ids.filtered(
                lambda l: "payment_term" == l.display_type
            )._compute_account_id()
        if lines_without_product:
            res["warning"] = {"title": _("Warning")}
            if len(lines_without_product) == len(invoice_lines):
                res["warning"]["message"] = _(
                    "The invoice lines were not updated to the new "
                    "Fiscal Position because they don't have products. "
                    "You should update the Account and the Taxes of each "
                    "invoice line manually."
                )
            else:
                res["warning"]["message"] = _(
                    "The following invoice lines were not updated "
                    "to the new Fiscal Position because they don't have a "
                    "Product:\n - %s\nYou should update the Account and the "
                    "Taxes of these invoice lines manually."
                ) % ("\n- ".join(lines_without_product.mapped("name")))
        return res

    @api.depends('company_id')
    def _compute_partner_bank_id(self):
        """ Update bank accounts if company is changed"""
        super()._compute_partner_bank_id()
