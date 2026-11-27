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

    def action_archive(self):
        res = super().action_archive()
        if warning := self._get_parent_cost_archive_warning():
            return warning
        return res

    def _get_shared_categories(self, company, shared):
        return (
            self.env["product.category"]
            .sudo()
            .with_company(company.root_id)
            .search([("shared_to_branches", "=", shared)])
        )

    def _check_shared_valuation_branch(self):
        """A branch cannot have a warehouse while its root shares a stock valuation.

        'Stock on the parent' is meant for stock on the parent and branches that
        only invoice: with stock on a branch, its moves would be valued at the
        branch's own cost.
        """
        for warehouse in self:
            company = warehouse.company_id
            if not company.parent_id:
                continue
            categories = self._get_shared_categories(company, "parent_stock")
            if categories:
                raise UserError(
                    self.env._(
                        "%(branch)s is a branch of %(root)s, which shares the stock valuation of "
                        "%(count)s product categories to its branches (for example, %(categories)s). "
                        "That setup is meant for stock on the parent company only, so a branch "
                        "cannot have a warehouse. Set 'Shared Stock Valuation to Branches' to "
                        "another option on those categories first.",
                        branch=company.name,
                        root=company.root_id.name,
                        count=len(categories),
                        categories=", ".join(categories[:3].mapped("display_name")),
                    )
                )

    def _get_parent_cost_archive_warning(self):
        """Warn, without blocking, when a branch is left with no warehouse under 'parent_cost'."""
        branches = self.company_id.filtered("parent_id")
        affected = branches.filtered(
            lambda b: b in b._get_branches_without_warehouse() and self._get_shared_categories(b, "parent_cost")
        )
        if not affected:
            return False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "sticky": True,
                "title": self.env._("Branch without warehouse"),
                "message": self.env._(
                    "%(branches)s no longer have an active warehouse, but their parent company values "
                    "some product categories with 'Parent's cost, stock on the branches'. That option "
                    "needs a warehouse on every branch: the stock and the cost of these branches will "
                    "not work as expected until they have one again, or the categories use another option.",
                    branches=", ".join(affected.mapped("name")),
                ),
            },
        }
