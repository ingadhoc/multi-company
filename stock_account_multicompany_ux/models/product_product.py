from odoo import api, fields, models
from odoo.exceptions import UserError

# Costs of a shared product that the branches copy from the root. The second one
# comes from stock_currency_valuation, when it is installed.
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
                is_branch and product.categ_id.sudo().with_company(root_company).shared_to_branches
            )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # Created from a branch, a shared product still takes the root's cost.
        products.with_company(self.env.company.root_id)._sync_shared_cost_to_branches()
        return products

    def write(self, vals):
        cost_change = SHARED_COST_FIELDS & vals.keys()
        if (
            cost_change
            and not self.env.context.get("shared_valuation_sync")
            and not self.env.context.get("disable_auto_revaluation")
        ):
            self._check_branch_cost_change()
        res = super().write(vals)
        if cost_change:
            self._sync_shared_cost_to_branches()
        return res

    def _get_shared_costs(self):
        """The costs a branch copies from the root, as {field: value}.

        Besides the cost, the cost in the secondary valuation currency when
        stock_currency_valuation is installed.
        """
        self.ensure_one()
        return {fname: self[fname] for fname in SHARED_COST_FIELDS if fname in self._fields}

    def _get_shared_cost_products(self, root_company):
        """Products whose cost the root company shares with its branches.

        Lot valuation keeps a cost per lot, so it is left out.
        """
        return self.filtered(
            lambda p: p.categ_id.sudo().with_company(root_company).shared_to_branches and not p.lot_valuated
        )

    def _check_branch_cost_change(self):
        company = self.env.company
        if not company.parent_id:
            return
        shared = self.filtered(lambda p: p.categ_id.sudo().with_company(company.root_id).shared_to_branches)
        if shared:
            raise UserError(
                self.env._(
                    "The cost of %(products)s is shared to branches by %(root)s. Change it on %(root)s, "
                    "or disable 'Shared Stock Valuation to Branches' on its category to manage "
                    "each branch's cost on its own.",
                    products=", ".join(shared.mapped("display_name")),
                    root=company.root_id.name,
                )
            )

    def _get_shared_cost_branches(self):
        root = self.env.company
        return self.env["res.company"].sudo().search([("id", "child_of", root.id), ("id", "!=", root.id)])

    def _sync_shared_cost_to_branches(self):
        """Copy the root company's cost to every branch for shared products.

        With the same standard_price in every company, Odoo values the branch's moves
        and stock at the root's cost, and a cost change on the root revalues the
        branches' stock as well (a value adjustment of each branch).
        """
        company = self.env.company
        if company.parent_id or not company.child_ids:
            return
        products = self._get_shared_cost_products(company)
        if not products:
            return
        branches = self._get_shared_cost_branches()
        date = self.env.context.get("valuation_date") or fields.Datetime.now()
        for product in products:
            costs = product.sudo().with_company(company)._get_shared_costs()
            for branch in branches:
                branch_product = product.sudo().with_company(branch)
                if branch_product._get_shared_costs() != costs:
                    branch_product._set_shared_cost(costs, date)

    def _set_shared_cost(self, costs, date, description=None):
        """Set the costs of this branch product and revalue its stock from ``date``.

        The value adjustment is created here, not by Odoo's revaluation, because
        Odoo assigns it to the product's company: a product of the parent would
        revalue the parent instead of the branch.
        """
        self.ensure_one()
        branch = self.env.company
        self.with_context(shared_valuation_sync=True, disable_auto_revaluation=True).write(costs)
        value = {
            "product_id": self.id,
            "value": costs["standard_price"],
            "company_id": branch.id,
            "date": date,
            "description": description or self.env._("Cost shared by %(company)s", company=branch.root_id.name),
        }
        if "standard_price_in_currency" in costs and self.valuation_currency_id:
            value["value_in_currency"] = costs["standard_price_in_currency"]
            value["valuation_currency_id"] = self.valuation_currency_id.id
        self.env["product.value"].sudo().create(value)

    def _get_branch_shared_products(self):
        """Shared products, when valued from a branch: they go at the root's cost."""
        company = self.env.company
        if not company.parent_id:
            return self.browse()
        return self._get_shared_cost_products(company.root_id)

    def _get_shared_cost_at_date(self, at_date=None):
        self.ensure_one()
        if at_date and (
            value := self.with_context(exclude_min_valuation_date=True)._get_last_product_value(at_date).get(self)
        ):
            return value.value
        return self.standard_price

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """A branch values its FIFO stock and deliveries at the root's cost, not its own layers."""
        if self._get_branch_shared_products():
            return self._get_shared_cost_at_date(at_date) * quantity
        return super()._run_fifo(quantity, lot=lot, at_date=at_date, location=location)

    def _run_fifo_batch(self, at_date=None, lot=None, location=None):
        shared = self._get_branch_shared_products()
        if not shared:
            return super()._run_fifo_batch(at_date=at_date, lot=lot, location=location)
        std_prices, values = super(ProductProduct, self - shared)._run_fifo_batch(
            at_date=at_date, lot=lot, location=location
        )
        shared_prices, shared_values = shared._run_standard_batch(at_date=at_date, lot=lot)
        return {**std_prices, **shared_prices}, {**values, **shared_values}

    def _run_average_batch(self, at_date=None, lot=None, force_recompute=False):
        shared = self._get_branch_shared_products()
        if not shared:
            return super()._run_average_batch(at_date=at_date, lot=lot, force_recompute=force_recompute)
        std_prices, values = super(ProductProduct, self - shared)._run_average_batch(
            at_date=at_date, lot=lot, force_recompute=force_recompute
        )
        shared_prices, shared_values = shared._run_standard_batch(at_date=at_date, lot=lot)
        return {**std_prices, **shared_prices}, {**values, **shared_values}

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        """In a branch, shared products keep the root's cost instead of their own average."""
        company = self.env.company
        if not company.parent_id:
            return super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)
        shared = self._get_shared_cost_products(company.root_id)
        return super(ProductProduct, self - shared)._update_standard_price(
            extra_value=extra_value, extra_quantity=extra_quantity
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
