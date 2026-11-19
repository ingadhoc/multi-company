from odoo import api, fields, models
from odoo.exceptions import UserError

# Category fields the root company imposes on its branches when the valuation is shared.
SHARED_VALUATION_FIELDS = {
    "shared_to_branches",
    "property_cost_method",
    "property_valuation",
    "property_account_income_categ_id",
    "property_account_expense_categ_id",
    "property_stock_valuation_account_id",
    "property_price_difference_account_id",
    "property_stock_journal",
}


class ProductCategory(models.Model):
    """
    Extiende product.category para soportar la propagación de configuración
    de valoración de inventario desde una compañía padre hacia sus branches.

    El campo clave es 'shared_to_branches': cuando está activo en una categoría,
    todas las branches heredan el método de costeo y el precio estándar definidos
    en la compañía padre, garantizando un costo único para todo el grupo.
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

    shared_to_branches = fields.Boolean(
        string="Shared Stock Valuation to Branches",
        company_dependent=True,
        help=(
            "For a parent company that keeps the stock and the purchases while its "
            "branches only invoice (for example, a branch to invoice in B). The branches "
            "take the costing method, valuation and accounts of the parent, cannot change "
            "them, and their invoices take the cost of goods sold at the parent's cost.\n\n"
            "It does not apply when the branches have their own warehouses: their stock "
            "moves would be valued at each branch's own cost.\n\n"
            "This flag is company-dependent: it is edited on the group's root "
            "company and synced down to its branches, so each company group can "
            "decide independently which categories are shared."
        ),
    )

    can_share_to_branches = fields.Boolean(
        compute="_compute_can_share_to_branches",
        help="True when the active company is a parent with branches and no branch has "
        "an active warehouse: its stock lives on the parent and the branches only invoice.",
    )

    is_valuation_shared_from_parent = fields.Boolean(
        compute="_compute_is_valuation_shared_from_parent",
        help="True when the active company is a branch and the root company shares "
        "this category's valuation: the branch cannot change it.",
    )

    @api.depends_context("company")
    def _compute_can_share_to_branches(self):
        company = self.env.company
        self.can_share_to_branches = bool(
            not company.parent_id and company.child_ids and not company._get_branch_warehouses()
        )

    @api.depends_context("company")
    def _compute_is_valuation_shared_from_parent(self):
        company = self.env.company
        if not company.parent_id:
            self.is_valuation_shared_from_parent = False
            return
        for categ in self:
            categ.is_valuation_shared_from_parent = categ.sudo().with_company(company.root_id).shared_to_branches

    def write(self, vals):
        if not self.env.context.get("shared_valuation_sync"):
            if SHARED_VALUATION_FIELDS & vals.keys():
                self._check_branch_valuation_change()
            if vals.get("shared_to_branches"):
                self._check_share_to_branches()
        res = super().write(vals)
        # Si se modificaron campos de valoración o el flag 'shared_to_branches',
        # propagar la configuración a las branches para mantener coherencia.
        propagate_fields = {"shared_to_branches", "property_cost_method", "property_valuation"}
        if propagate_fields & vals.keys():
            self._propagate_valuation_to_branches()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        if any(vals.get("shared_to_branches") for vals in vals_list):
            self._check_share_to_branches()
        categs = super().create(vals_list)
        # Si la categoría se crea con shared_to_branches desde el inicio,
        # propagar la configuración de valoración a las branches inmediatamente.
        for categ, vals in zip(categs, vals_list):
            if vals.get("shared_to_branches"):
                categ._propagate_valuation_to_branches()
        return categs

    def _propagate_valuation_to_branches(self):
        """
        Sincroniza desde la compañía raíz (padre) hacia todas sus branches:

        - shared_to_branches: siempre (en ambos sentidos, on/off). Como es un
          campo company_dependent, la raíz es la fuente de verdad y las branches
          quedan en espejo; así cualquier lectura del flag en contexto de branch
          (stock_move, account_move_line, etc.) es coherente con la raíz.
        - property_cost_method y property_valuation: solo cuando la categoría
          está compartida, para imponer el costeo único del grupo. Si no está
          compartida, la branch gestiona su propia configuración.
        - Cuentas contables de la categoría (income, expense, valoración de
          stock, price difference / revaluación de costo) y el diario de stock:
          solo cuando está compartida. Se pisan siempre con el valor de la raíz
          para garantizar un mapeo contable único en todo el grupo. La cuenta de
          "Stock Variation" NO se propaga: es un related read-only de la cuenta
          de valoración, así que queda resuelta sola al propagar esta última.

        Solo propaga si el método se ejecuta en contexto de la compañía RAÍZ.
        Si se llama desde una branch (parent_id existe), se ignora para evitar
        propagaciones inversas o circulares (la escritura en cada branch vuelve
        a disparar write(), pero esta guardia corta la recursión).
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
            is_shared = root_categ.shared_to_branches

            # El flag se sincroniza siempre (también al desactivarlo).
            values = {"shared_to_branches": is_shared}
            # El costeo y las cuentas solo se imponen cuando está compartida.
            if is_shared:
                values["property_cost_method"] = root_categ.property_cost_method
                values["property_valuation"] = root_categ.property_valuation
                # Cuentas contables: se pisan siempre con el valor de la raíz
                # para garantizar un mapeo contable único en el grupo. Se toma
                # .id (False si la raíz no tiene valor → limpia la branch).
                # Stock Variation no va: es related de la cuenta de valoración.
                values.update(
                    {
                        "property_account_income_categ_id": root_categ.property_account_income_categ_id.id,
                        "property_account_expense_categ_id": root_categ.property_account_expense_categ_id.id,
                        "property_stock_valuation_account_id": root_categ.property_stock_valuation_account_id.id,
                        "property_price_difference_account_id": root_categ.property_price_difference_account_id.id,
                        "property_stock_journal": root_categ.property_stock_journal.id,
                    }
                )

            for branch in branches:
                categ.with_company(branch).with_context(shared_valuation_sync=True).write(values)

    def _check_branch_valuation_change(self):
        """A branch cannot change the valuation of a category the root shares."""
        company = self.env.company
        if not company.parent_id:
            return
        shared = self.filtered(lambda c: c.sudo().with_company(company.root_id).shared_to_branches)
        if shared:
            raise UserError(
                self.env._(
                    "The inventory valuation of %(categories)s is shared to branches by %(root)s. "
                    "Change it on %(root)s, or disable 'Shared Stock Valuation to Branches' there "
                    "to configure each branch on its own.",
                    categories=", ".join(shared.mapped("display_name")),
                    root=company.root_id.name,
                )
            )

    @api.model
    def _check_share_to_branches(self):
        """The valuation can only be shared while no branch has a warehouse."""
        company = self.env.company
        if company.parent_id:
            return
        warehouses = company._get_branch_warehouses()
        if warehouses:
            raise UserError(
                self.env._(
                    "'Shared Stock Valuation to Branches' is meant for stock on the parent company "
                    "and branches that only invoice. These branches of %(root)s have active "
                    "warehouses: %(branches)s. Their stock would be valued at each branch's own "
                    "cost, so the valuation cannot be shared.",
                    root=company.name,
                    branches=", ".join(sorted(set(warehouses.company_id.mapped("name")))),
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
