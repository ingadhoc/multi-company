from odoo import api, fields, models
from odoo.exceptions import UserError

SHARED_VALUATION_SELECTION = [
    ("none", "Not shared"),
    ("parent_stock", "Stock on the parent"),
    ("parent_cost", "Parent's cost, stock on the branches"),
]

# Category fields the root company imposes on its branches, by shared valuation.
SHARED_VALUATION_FIELDS = {
    "parent_stock": {
        "shared_to_branches",
        "property_cost_method",
        "property_valuation",
        "property_account_income_categ_id",
        "property_account_expense_categ_id",
        "property_stock_valuation_account_id",
        "property_price_difference_account_id",
        "property_stock_journal",
    },
    "parent_cost": {
        "shared_to_branches",
        "property_cost_method",
        # stock_currency_valuation, when it is installed
        "valuation_currency_id",
    },
}


class ProductCategory(models.Model):
    """
    Extiende product.category para soportar la propagación de configuración
    de valoración de inventario desde una compañía padre hacia sus branches.

    El campo clave es 'shared_to_branches', con tres opciones:

    - none: cada compañía valúa por su cuenta.
    - parent_stock: el stock vive en la padre y las branches solo facturan
      (caso A/B); las branches heredan la valuación y las cuentas de la padre.
    - parent_cost: cada branch tiene su stock, valuado a costo estándar con el
      costo que fija la padre; la valuación (periódica o perpetua) es la suya.
    """

    _inherit = "product.category"

    is_branch_company = fields.Boolean(
        compute="_compute_is_branch_company",
        help="True when the active company is a branch (has a parent company).",
    )

    company_has_branches = fields.Boolean(
        compute="_compute_is_branch_company",
        help="True when the active company has branches (child companies). "
        "shared_to_branches solo tiene sentido cuando la compañía realmente "
        "tiene branches, por eso el campo se oculta en compañías standalone.",
    )

    shared_to_branches = fields.Selection(
        selection=SHARED_VALUATION_SELECTION,
        string="Shared Stock Valuation to Branches",
        company_dependent=True,
        default="none",
        help=(
            "Not shared: the parent and each branch value their stock on their own.\n\n"
            "Stock on the parent: for a parent company that keeps the stock and the "
            "purchases while its branches only invoice (for example, a branch to invoice "
            "in B). The branches take the costing method, valuation and accounts of the "
            "parent, cannot change them, and their invoices take the cost of goods sold "
            "at the parent's cost. Only while no branch has a warehouse.\n\n"
            "Parent's cost, stock on the branches: every branch keeps stock in its own "
            "warehouses, valued at standard cost whatever the parent uses, with its own "
            "inventory valuation (periodic or perpetual). The cost is the parent's one: "
            "the parent's purchases set it, the branches' purchases do not change it, and an average cost on the parent "
            "counts the quantities of the branches too. Only while every branch has a "
            "warehouse.\n\n"
            "This field is company-dependent: it is edited on the group's root "
            "company and synced down to its branches, so each company group can "
            "decide independently which categories are shared."
        ),
    )

    can_share_parent_stock = fields.Boolean(
        compute="_compute_can_share",
        help="True when the active company is a parent with branches and no branch has "
        "an active warehouse: its stock lives on the parent and the branches only invoice.",
    )

    can_share_parent_cost = fields.Boolean(
        compute="_compute_can_share",
        help="True when the active company is a parent with branches and every branch " "has an active warehouse.",
    )

    parent_shared_valuation = fields.Selection(
        selection=SHARED_VALUATION_SELECTION,
        compute="_compute_is_valuation_shared_from_parent",
        help="Shared valuation the root company sets for this category, seen from a branch.",
    )

    is_valuation_shared_from_parent = fields.Boolean(
        compute="_compute_is_valuation_shared_from_parent",
        help="True when the active company is a branch and the root company shares "
        "this category's valuation: the branch cannot change it.",
    )

    @api.depends_context("company")
    def _compute_can_share(self):
        company = self.env.company
        is_root = not company.parent_id and bool(company.child_ids)
        self.can_share_parent_stock = is_root and not company._get_branch_warehouses()
        self.can_share_parent_cost = is_root and not company._get_branches_without_warehouse()

    @api.depends_context("company")
    def _compute_is_valuation_shared_from_parent(self):
        company = self.env.company
        if not company.parent_id:
            self.is_valuation_shared_from_parent = False
            self.parent_shared_valuation = "none"
            return
        for categ in self:
            categ.parent_shared_valuation = categ._get_shared_valuation()
            categ.is_valuation_shared_from_parent = categ.parent_shared_valuation != "none"

    def _get_shared_valuation(self, company=None):
        """Shared valuation the root company of ``company`` (the active one by default) sets."""
        if not self:
            return "none"
        self.ensure_one()
        root = (company or self.env.company).root_id
        return self.sudo().with_company(root).shared_to_branches or "none"

    def write(self, vals):
        if not self.env.context.get("shared_valuation_sync"):
            self._check_branch_valuation_change(vals.keys())
            if vals.get("shared_to_branches", "none") != "none":
                self._check_share_to_branches(vals["shared_to_branches"])
        res = super().write(vals)
        # Si se modificaron campos de valoración o el flag 'shared_to_branches',
        # propagar la configuración a las branches para mantener coherencia.
        propagate_fields = {"shared_to_branches", "property_cost_method", "property_valuation", "valuation_currency_id"}
        if propagate_fields & vals.keys():
            self._propagate_valuation_to_branches()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for shared in {vals.get("shared_to_branches", "none") for vals in vals_list} - {"none"}:
            self._check_share_to_branches(shared)
        categs = super().create(vals_list)
        # Si la categoría se crea con shared_to_branches desde el inicio,
        # propagar la configuración de valoración a las branches inmediatamente.
        for categ, vals in zip(categs, vals_list):
            if vals.get("shared_to_branches", "none") != "none":
                categ._propagate_valuation_to_branches()
        return categs

    def _propagate_valuation_to_branches(self):
        """
        Sincroniza desde la compañía raíz (padre) hacia todas sus branches:

        - shared_to_branches: siempre (también al pasar a none). Como es un
          campo company_dependent, la raíz es la fuente de verdad y las branches
          quedan en espejo; así cualquier lectura del flag en contexto de branch
          (stock_move, account_move_line, etc.) es coherente con la raíz.
        - parent_stock: método de costeo, valuación, cuentas contables de la
          categoría (income, expense, valoración de stock, price difference) y
          diario de stock, pisados con el valor de la raíz para un mapeo contable
          único en el grupo. La cuenta de "Stock Variation" NO se propaga: es un
          related read-only de la cuenta de valoración.
        - parent_cost: la branch queda en costo estándar, sea cual sea el método
          de la raíz, y toma el costo de la raíz. La valuación y las cuentas
          siguen siendo las de cada branch.
        - none: la branch gestiona su propia configuración.

        Solo propaga si el método se ejecuta en contexto de la compañía RAÍZ.
        Si se llama desde una branch (parent_id existe), se ignora para evitar
        propagaciones inversas o circulares.
        """
        root_company = self.env.company

        # Guardia: solo propagar desde la compañía raíz, nunca desde una branch.
        if root_company.parent_id:
            return

        # Obtener las branches accesibles (excluye a la propia compañía raíz)
        branches = root_company._accessible_branches() - root_company
        if not branches:
            return

        for categ in self:
            root_categ = categ.with_company(root_company)
            shared = root_categ.shared_to_branches or "none"

            values = {"shared_to_branches": shared}
            if shared == "parent_stock":
                values.update(
                    {
                        "property_cost_method": root_categ.property_cost_method,
                        "property_valuation": root_categ.property_valuation,
                        "property_account_income_categ_id": root_categ.property_account_income_categ_id.id,
                        "property_account_expense_categ_id": root_categ.property_account_expense_categ_id.id,
                        "property_stock_valuation_account_id": root_categ.property_stock_valuation_account_id.id,
                        "property_price_difference_account_id": root_categ.property_price_difference_account_id.id,
                        "property_stock_journal": root_categ.property_stock_journal.id,
                    }
                )
            elif shared == "parent_cost":
                values["property_cost_method"] = "standard"
                if "valuation_currency_id" in categ._fields:
                    values["valuation_currency_id"] = root_categ.valuation_currency_id.id

            for branch in branches:
                categ.with_company(branch).with_context(shared_valuation_sync=True).write(values)

            if shared == "parent_cost":
                self.env["product.product"].with_context(active_test=False).search(
                    [("categ_id", "=", categ.id)]
                )._sync_shared_cost_to_branches()

    def _check_branch_valuation_change(self, fnames):
        """A branch cannot change what the root imposes on a category it shares."""
        company = self.env.company
        if not company.parent_id:
            return
        shared = self.filtered(lambda c: SHARED_VALUATION_FIELDS.get(c._get_shared_valuation(), set()) & fnames)
        if shared:
            raise UserError(
                self.env._(
                    "The inventory valuation of %(categories)s is shared to branches by %(root)s. "
                    "Change it on %(root)s, or set 'Shared Stock Valuation to Branches' to "
                    "'Not shared' there to configure each branch on its own.",
                    categories=", ".join(shared.mapped("display_name")),
                    root=company.root_id.name,
                )
            )

    @api.model
    def _check_share_to_branches(self, shared):
        """Stock on the parent needs no branch warehouse; the parent's cost needs one on every branch."""
        company = self.env.company
        if company.parent_id:
            return
        if shared == "parent_stock":
            warehouses = company._get_branch_warehouses()
            if warehouses:
                raise UserError(
                    self.env._(
                        "'Stock on the parent' is meant for stock on the parent company and "
                        "branches that only invoice. These branches of %(root)s have active "
                        "warehouses: %(branches)s. Their stock would be valued at each branch's own "
                        "cost, so the valuation cannot be shared this way.",
                        root=company.name,
                        branches=", ".join(sorted(set(warehouses.company_id.mapped("name")))),
                    )
                )
        elif shared == "parent_cost":
            if not company.child_ids:
                raise UserError(self.env._("%(company)s has no branches to share its cost with.", company=company.name))
            without_warehouse = company._get_branches_without_warehouse()
            if without_warehouse:
                raise UserError(
                    self.env._(
                        "'Parent's cost, stock on the branches' needs a warehouse on every branch "
                        "of %(root)s. These branches have none: %(branches)s.",
                        root=company.name,
                        branches=", ".join(sorted(without_warehouse.mapped("name"))),
                    )
                )

    @api.depends_context("company")
    def _compute_is_branch_company(self):
        """
        Calcula dos flags sobre la compañía activa (dependen del contexto de
        compañía para recalcularse al cambiar de empresa):

        - is_branch_company: la compañía activa es una branch (tiene parent_id).
        - company_has_branches: la compañía activa tiene branches (child_ids).

        Se usan en la vista para mostrar shared_to_branches únicamente en
        compañías padre que efectivamente tienen branches (no en branches ni en
        compañías standalone sin hijos).
        """
        company = self.env.company
        is_branch = bool(company.parent_id)
        has_branches = bool(company.child_ids)
        for categ in self:
            categ.is_branch_company = is_branch
            categ.company_has_branches = has_branches
