from odoo import api, models
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        warehouses._check_shared_valuation_branch()
        return warehouses

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active") or "company_id" in vals:
            self.filtered("active")._check_shared_valuation_branch()
        return res

    def _check_shared_valuation_branch(self):
        """A branch cannot have a warehouse while its root shares a stock valuation.

        'Shared Stock Valuation to Branches' is meant for stock on the parent and
        branches that only invoice: with stock on a branch, its moves would be valued
        at the branch's own cost.
        """
        for warehouse in self:
            company = warehouse.company_id
            if not company.parent_id:
                continue
            categories = (
                self.env["product.category"]
                .sudo()
                .with_company(company.root_id)
                .search([("shared_to_branches", "=", True)])
            )
            if categories:
                raise UserError(
                    self.env._(
                        "%(branch)s is a branch of %(root)s, which shares the stock valuation of "
                        "%(count)s product categories to its branches (for example, %(categories)s). "
                        "That setup is meant for stock on the parent company only, so a branch "
                        "cannot have a warehouse. Disable 'Shared Stock Valuation to Branches' on "
                        "those categories first.",
                        branch=company.name,
                        root=company.root_id.name,
                        count=len(categories),
                        categories=", ".join(categories[:3].mapped("display_name")),
                    )
                )
