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

    shared_to_branches = fields.Boolean(
        string="Shared Stock Valuation to Branches",
        help=(
            "When enabled, all branches of the parent company will use the same "
            "costing method and standard price defined in the parent company for "
            "products in this category. This ensures a single unified cost across "
            "the parent and all its branches."
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
        Copia property_cost_method y property_valuation desde la compañía activa
        (padre) hacia todas las branches accesibles, para cada categoría que tenga
        'shared_to_branches' habilitado.

        Solo propaga si el método es llamado en contexto de la compañía PADRE.
        Si se llama desde una branch (parent_id existe), se ignora para evitar
        propagaciones inversas o circulares.
        """
        for categ in self.filtered("shared_to_branches"):
            parent_company = self.env.company

            # Guardia: solo propagar desde la compañía padre, nunca desde una branch.
            if parent_company.parent_id:
                continue

            # Obtener las branches accesibles (excluye a la propia compañía padre)
            branches = parent_company._accessible_branches() - parent_company
            if not branches:
                continue

            # Leer la configuración de valoración definida en el padre
            parent_cost_method = categ.with_company(parent_company).property_cost_method
            parent_valuation = categ.with_company(parent_company).property_valuation

            # Escribir la misma configuración en el contexto de cada branch
            for branch in branches:
                categ.with_company(branch).write(
                    {
                        "property_cost_method": parent_cost_method,
                        "property_valuation": parent_valuation,
                    }
                )

    @api.depends_context("company")
    def _compute_is_branch_company(self):
        """
        Indica si la compañía activa es una branch (tiene parent_id).
        Depende del contexto de compañía para recalcularse al cambiar de empresa.
        Se usa en la vista para mostrar/ocultar campos relevantes solo para branches.
        """
        is_branch = bool(self.env.company.parent_id)
        for categ in self:
            categ.is_branch_company = is_branch
