##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        """On downpayment lines odoo reuses the account of the already invoiced
        downpayment without checking its company. If that invoice was moved to another
        company (the change company wizard, or just picking a journal of another company
        while it was a draft), the account is not valid on the invoice being created and
        it is rejected with "Incompatible companies on records". Take the downpayment
        account of the company of the new invoice instead, and if there is none drop the
        account so that account.move.line computes it."""
        res = super()._prepare_invoice_line(**optional_values)
        account = self.env["account.account"].browse(res.get("account_id"))
        if not account or account.filtered_domain(account._check_company_domain(self.company_id)):
            return res
        # the invoice is not always created in the company of the order, another module
        # can send it elsewhere, so the company is resolved before replacing anything
        company = self._get_invoice_company()
        if not company or account.filtered_domain(account._check_company_domain(company)):
            return res
        del res["account_id"]
        account = self._get_downpayment_account(company)
        if account:
            res["account_id"] = account.id
        return res

    def _get_invoice_company(self):
        self.ensure_one()
        return self.env["res.company"].browse(self.order_id._prepare_invoice().get("company_id"))

    def _get_downpayment_account(self, company):
        """Downpayment account of the given company, with the same criteria the advance
        payment wizard applies: the account configured on the company, and the
        downpayment or income account of the products otherwise."""
        fiscal_pos = self.order_id.fiscal_position_id
        account = company.downpayment_account_id
        if account:
            return fiscal_pos.map_account(account) if fiscal_pos else account
        # a downpayment line may have no product of its own, or one without accounts, so
        # the search continues on the products of the order
        templates = self.product_id.product_tmpl_id | self.order_id.order_line.product_id.product_tmpl_id
        for template in templates:
            accounts = template.with_company(company).get_product_accounts(fiscal_pos=fiscal_pos)
            account = accounts.get("downpayment") or accounts.get("income")
            if account and account.filtered_domain(account._check_company_domain(company)):
                return account
        return self.env["account.account"]
