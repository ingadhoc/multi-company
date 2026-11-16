from odoo import models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    def stock_accounting_value(self, accounts_by_product=None, at_date=None):
        """Accounting value of the stock of the company that holds it.

        A company of the group may invoice goods moved by another one: a sale of the
        parent invoiced in the branch, or a purchase received in the parent and billed
        in the branch. Those valuation lines are posted by the invoicing company but
        move the other company's stock, so they count for that company. Everything
        else (closings, the company's own receipts and deliveries) stays where it was
        posted.
        """
        self.ensure_one()
        if not (self.parent_id or self.child_ids):
            return super().stock_accounting_value(accounts_by_product=accounts_by_product, at_date=at_date)
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()
        account_data = super().stock_accounting_value(accounts_by_product=accounts_by_product, at_date=at_date)

        valuation_account_ids = {accounts["valuation"].id for accounts in accounts_by_product.values()}
        group = self.sudo().search([("id", "child_of", self.root_id.id)])
        domain = Domain(
            [
                ("account_id", "in", list(valuation_account_ids)),
                ("parent_state", "=", "posted"),
                ("display_type", "in", ["cogs", "product"]),
                ("company_id", "in", group.ids),
            ]
        )
        if at_date:
            domain &= Domain([("date", "<=", at_date)])
        for line in self.env["account.move.line"].sudo().search(domain):
            stock_company = line._get_stock_valuation_company()
            if stock_company == line.company_id:
                continue
            if line.company_id == self:
                account_data[line.account_id] -= line.balance
            elif stock_company == self:
                account_data[line.account_id] += line.balance
        return account_data
