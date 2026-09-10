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
        while it was a draft), the account is not valid here and the final invoice is
        rejected with "Incompatible companies on records". Take the downpayment account
        of the order company instead, and if there is none drop the account so that
        account.move.line computes it."""
        res = super()._prepare_invoice_line(**optional_values)
        account = self.env["account.account"].browse(res.get("account_id"))
        company = self.company_id
        if not account or not company or account.filtered_domain(account._check_company_domain(company)):
            return res
        del res["account_id"]
        # a downpayment line may have no product of its own, or one without accounts, so
        # the search continues on the products of the order as the change company wizard does
        templates = self.product_id.product_tmpl_id | self.order_id.order_line.product_id.product_tmpl_id
        fiscal_pos = self.order_id.fiscal_position_id
        for template in templates:
            account = template._get_downpayment_or_income_account(company, fiscal_pos)
            if account.filtered_domain(account._check_company_domain(company)):
                res["account_id"] = account.id
                break
        return res
