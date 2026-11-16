import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Give the branches the parent's cost history for shared categories.

    Until now the branches kept their own cost (usually 0) for shared products, so
    the stock in their warehouses was valued at 0. Each cost the parent had is
    copied to every branch with its own date, so the stock of a branch is valued
    at the parent's cost from the day the parent had it, and the stock closing of
    any period after that date posts it.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    roots = env["res.company"].search([("parent_id", "=", False), ("child_ids", "!=", False)])
    for root in roots:
        categs = env["product.category"].with_company(root).search([("shared_to_branches", "=", True)])
        if not categs:
            continue
        products = (
            env["product.product"]
            .with_company(root)
            .with_context(active_test=False)
            .search([("categ_id", "in", categs.ids)])
            ._get_shared_cost_products(root)
        )
        branches = products._get_shared_cost_branches()
        if "valuation_currency_id" in categs._fields:
            for categ in categs:
                for branch in branches:
                    categ.with_company(branch).with_context(shared_valuation_sync=True).write(
                        {"valuation_currency_id": categ.valuation_currency_id.id}
                    )
        cost_domain = [("product_id", "in", products.ids), ("move_id", "=", False), ("lot_id", "=", False)]
        # The branches' own costs of these products were never meant to exist: left in
        # place they would win over the copied history at past dates.
        own_costs = env["product.value"].search(cost_domain + [("company_id", "in", branches.ids)])
        _logger.info(
            "Replacing %s own cost records of the branches of %s by the cost history of %s products",
            len(own_costs),
            root.name,
            len(products),
        )
        own_costs.unlink()
        history = env["product.value"].search(cost_domain + [("company_id", "=", root.id)], order="date, id")
        for product in products:
            product_history = history.filtered(lambda v, p=product: v.product_id == p)
            for branch in branches:
                branch_product = product.with_company(branch)
                for value in product_history:
                    costs = {"standard_price": value.value}
                    if "value_in_currency" in value._fields:
                        costs["standard_price_in_currency"] = value.value_in_currency
                    branch_product._set_shared_cost(costs, value.date, description=value.description)
                # An average or FIFO cost moves without a value adjustment: bring it up to date.
                costs = product._get_shared_costs()
                if branch_product._get_shared_costs() != costs:
                    branch_product._set_shared_cost(costs, env.cr.now())
