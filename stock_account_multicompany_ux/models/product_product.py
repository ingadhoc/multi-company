from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import float_compare

# Costs a branch copies from the root. The second one comes from
# stock_currency_valuation, when it is installed.
SHARED_COST_FIELDS = {"standard_price", "standard_price_in_currency"}


class ProductProduct(models.Model):
    """
    Extiende product.product para mostrar, parado en una branch, el costo
    (standard_price) definido en la compañía raíz del grupo cuando la categoría
    del producto está marcada como 'shared_to_branches'.

    standard_price es un campo company_dependent: cada compañía guarda su propio
    valor. En una branch ese valor suele estar vacío/0, porque el costo del grupo
    se define en el padre. Para que el usuario vea el costo correcto sin alterar
    el storage ni la valoración contable, se expone un campo computado de solo
    lectura ('parent_standard_price') que la vista muestra en lugar de
    standard_price cuando corresponde.
    """

    _inherit = "product.product"

    is_cost_shared_from_parent = fields.Boolean(
        compute="_compute_is_cost_shared_from_parent",
        help="True cuando la compañía activa es una branch y la categoría del "
        "producto está compartida a branches: el costo debe leerse de la "
        "compañía raíz del grupo, no de la branch.",
    )
    parent_standard_price = fields.Float(
        string="Cost (Parent Company)",
        compute="_compute_parent_standard_price",
        digits="Product Price",
        groups="base.group_user",
        help="Costo de solo lectura que se muestra en las branches para "
        "productos cuya categoría está compartida a branches. El valor se "
        "toma de la compañía raíz del grupo, de modo que todo el grupo "
        "muestre un único costo unificado.",
    )

    @api.depends_context("company")
    @api.depends("categ_id.shared_to_branches")
    def _compute_is_cost_shared_from_parent(self):
        company = self.env.company
        is_branch = bool(company.parent_id)
        # shared_to_branches es company_dependent y se edita en la raíz del grupo:
        # lo leemos siempre en ese contexto para no depender del valor sincronizado
        # en la branch.
        root_company = company.root_id
        for product in self:
            product.is_cost_shared_from_parent = (
                is_branch and product.categ_id._get_shared_valuation(root_company) != "none"
            )

    @api.depends_context("company")
    @api.depends("standard_price", "categ_id.shared_to_branches")
    def _compute_parent_standard_price(self):
        root_company = self.env.company.root_id
        for product in self:
            if product.is_cost_shared_from_parent:
                product.parent_standard_price = product.sudo().with_company(root_company).standard_price
            else:
                product.parent_standard_price = product.standard_price

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # Created from a branch, a product still takes the root's cost.
        products.with_company(self.env.company.root_id)._sync_shared_cost_to_branches()
        return products

    def write(self, vals):
        # Odoo's own cost updates (average cost, FIFO) pass disable_auto_revaluation.
        if "standard_price" in vals and not self.env.context.get("disable_auto_revaluation"):
            self._check_branch_cost_change(vals["standard_price"])
        res = super().write(vals)
        if SHARED_COST_FIELDS & vals.keys():
            self._sync_shared_cost_to_branches()
        return res

    def _check_branch_cost_change(self, new_cost):
        """A branch cannot change the cost of a product whose category the root shares.

        Writing the same cost is let through: creating a product writes its cost.
        """
        company = self.env.company
        if not company.parent_id:
            return
        digits = self.env["decimal.precision"].precision_get("Product Price")
        shared = self.filtered(
            lambda p: p.categ_id._get_shared_valuation() != "none"
            and float_compare(p.standard_price, new_cost or 0.0, precision_digits=digits)
        )
        if shared:
            raise UserError(
                self.env._(
                    "The cost of %(products)s is shared to branches by %(root)s. Change it on %(root)s, "
                    "or set 'Shared Stock Valuation to Branches' to 'Not shared' on its category to "
                    "manage each branch's cost on its own.",
                    products=", ".join(shared[:5].mapped("display_name")),
                    root=company.root_id.name,
                )
            )

    # -------------------------------------------------------------------------
    # Parent's cost, stock on the branches (parent_cost)
    # -------------------------------------------------------------------------

    def _get_parent_cost_products(self):
        """Products whose cost the root company sets for its branches' stock.

        Lot valuation keeps a cost per lot, so it is left out.
        """
        root = self.env.company.root_id
        return self.filtered(lambda p: not p.lot_valuated and p.categ_id._get_shared_valuation(root) == "parent_cost")

    def _get_shared_costs(self):
        """The costs a branch copies from the root, as {field: value}."""
        self.ensure_one()
        return {fname: self[fname] for fname in SHARED_COST_FIELDS if fname in self._fields}

    def _sync_shared_cost_to_branches(self):
        """Copy the root company's cost to every branch, for parent_cost products.

        The branches value them at standard cost: with the root's cost, a cost change
        on the root revalues the branches' stock as well, in their next closing.
        """
        company = self.env.company
        if company.parent_id or not company.child_ids:
            return
        products = self._get_parent_cost_products()
        if not products:
            return
        branches = self.env["res.company"].sudo().search([("id", "child_of", company.id), ("id", "!=", company.id)])
        date = self.env.context.get("valuation_date") or fields.Datetime.now()
        for product in products:
            costs = product.sudo().with_company(company)._get_shared_costs()
            for branch in branches:
                branch_product = product.sudo().with_company(branch)
                if branch_product._get_shared_costs() != costs:
                    branch_product._set_shared_cost(costs, date)

    def _set_shared_cost(self, costs, date):
        """Set the costs of this branch product, with its cost history from ``date``.

        The product.value is created here, not by Odoo's revaluation, because Odoo
        assigns it to the product's company: a product of the parent would get the
        parent's cost history instead of the branch's one.
        """
        self.ensure_one()
        branch = self.env.company
        self.with_context(shared_valuation_sync=True, disable_auto_revaluation=True).write(costs)
        value = {
            "product_id": self.id,
            "value": costs["standard_price"],
            "company_id": branch.id,
            "date": date,
            "description": self.env._("Cost set by %(company)s", company=branch.root_id.name),
        }
        if "standard_price_in_currency" in costs and self.valuation_currency_id:
            value["value_in_currency"] = costs["standard_price_in_currency"]
            value["valuation_currency_id"] = self.valuation_currency_id.id
        self.env["product.value"].sudo().create(value)

    def _get_group_average_products(self):
        """parent_cost products with average cost, valued from the root company.

        Their average counts the quantities in the branches' warehouses too.
        """
        company = self.env.company
        if company.parent_id or not company.child_ids:
            return self.browse()
        return self._get_parent_cost_products().filtered(lambda p: p.cost_method == "average")

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        # The incremental update only knows the root's quantity: recompute them in full.
        group_products = self._get_group_average_products()
        if group_products and extra_value is not None and extra_quantity is not None:
            extra_value = {p: v for p, v in extra_value.items() if p not in group_products}
            extra_quantity = {p: q for p, q in extra_quantity.items() if p not in group_products}
        return super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)

    def _run_average_batch(self, at_date=None, lot=None, force_recompute=False):
        group_products = self._get_group_average_products()
        if lot or not group_products or (not at_date and not force_recompute):
            return super()._run_average_batch(at_date=at_date, lot=lot, force_recompute=force_recompute)
        prices, values = super(ProductProduct, self - group_products)._run_average_batch(
            at_date=at_date, lot=lot, force_recompute=force_recompute
        )
        group_prices, group_values = group_products._run_group_average_batch(at_date=at_date)
        return {**prices, **group_prices}, {**values, **group_values}

    def _run_group_average_batch(self, at_date=None):
        """Average cost of the root company, counting the stock of its branches.

        Only the root's receipts set the cost. The branches' moves add or take
        quantity at the current average: a branch purchase does not change the cost,
        but the units it holds weigh on the next average. Moves between the root and
        a branch take out on one side what they bring in on the other.

        :return: ({product_id: average cost}, {product_id: value of the root's own stock})
        """
        root = self.env.company
        group = self.env["res.company"].sudo().search([("id", "child_of", root.id)])
        last_values = self._get_last_product_value(at_date)
        prices, values = {}, {}
        for product in self:
            domain = Domain(
                [
                    ("product_id", "=", product.id),
                    ("company_id", "in", group.ids),
                    "|",
                    ("is_in", "=", True),
                    ("is_out", "=", True),
                ]
            )
            if at_date:
                domain &= Domain([("date", "<=", at_date)])
            average = None
            quantity = root_quantity = 0.0
            if manual := last_values.get(product):
                domain &= Domain([("date", ">", manual.date)])
                average = manual.value
                quantity = product.with_context(to_date=manual.date, allowed_company_ids=group.ids).qty_available
                root_quantity = product.with_context(to_date=manual.date, allowed_company_ids=root.ids).qty_available
            for move in self.env["stock.move"].sudo().search(domain, order="date, id"):
                move_qty = move._get_valued_qty()
                own = move.company_id == root
                if move.is_in:
                    if own:
                        if average is not None and quantity > 0:
                            average = (average * quantity + move.value) / (quantity + move_qty)
                        elif move_qty:
                            average = move.value / move_qty
                        root_quantity += move_qty
                    quantity += move_qty
                if move.is_out:
                    quantity -= move_qty
                    if own:
                        root_quantity -= move_qty
            prices[product.id] = product.standard_price if average is None else average
            values[product.id] = prices[product.id] * root_quantity
        return prices, values
