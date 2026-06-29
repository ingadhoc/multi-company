from odoo import api, fields, models


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
            "When enabled, all branches of the parent company will use the same "
            "costing method and standard price defined in the parent company for "
            "products in this category. This ensures a single unified cost across "
            "the parent and all its branches.\n\n"
            "This flag is company-dependent: it is edited on the group's root "
            "company and synced down to its branches, so each company group can "
            "decide independently which categories are shared."
        ),
    )

    def write(self, vals):
        res = super().write(vals)
        # Si se modificaron campos de valoración o el flag 'shared_to_branches',
        # propagar la configuración a las branches para mantener coherencia.
        propagate_fields = {"shared_to_branches", "property_cost_method", "property_valuation"}
        if propagate_fields & vals.keys():
            self._propagate_valuation_to_branches()
        return res

    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
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
            # El costeo solo se impone cuando la categoría está compartida.
            if is_shared:
                values["property_cost_method"] = root_categ.property_cost_method
                values["property_valuation"] = root_categ.property_valuation

            for branch in branches:
                categ.with_company(branch).write(values)

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
