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

            # Productos de la categoría cuyo costo (standard_price, campo
            # company-dependent) se unifica con el del padre.
            products = self.env["product.product"].with_context(active_test=False).search([("categ_id", "=", categ.id)])
            parent_cost_by_product = {
                product.id: product.with_company(parent_company).standard_price for product in products
            }

            # Escribir la misma configuración en el contexto de cada branch
            for branch in branches:
                categ.with_company(branch).write(
                    {
                        "property_cost_method": parent_cost_method,
                        "property_valuation": parent_valuation,
                    }
                )

                # Traer el costo del padre a la branch SIN revaluar: usamos el
                # contexto disable_auto_revaluation para no generar SVL ni asiento
                # contable en la branch. Esto es coherente con que el módulo ya
                # excluye estos productos de la valoración de la branch
                # (ver res.company.stock_accounting_value); el inventario y su
                # valoración viven en el padre, la branch solo refleja el costo.
                for product in products:
                    product.with_company(branch).with_context(
                        disable_auto_revaluation=True
                    ).standard_price = parent_cost_by_product[product.id]

    @api.model
    def activate_shared_to_branches_for_ab(self):
        """Activa 'shared_to_branches' en las categorías cuya valoración es
        automatizada (real_time) tanto en la compañía padre como en sus branches.

        Pensado para correr post-migración en setups A/B (company merge): la
        migración deja esas categorías sin el flag tildado, lo que impide que el
        costo se comparta padre↔branches. Este método detecta los casos y activa
        el flag desde el contexto del padre, disparando la propagación de
        método de costeo, valoración y costo hacia las branches.

        Método público a propósito: además del post-migration del módulo, lo
        invoca por RPC (odooly) la UL 2379 ("Shared to branches en Valoración
        automatica de stock con A y B"). RPC bloquea métodos con guion bajo.

        Criterio: la categoría es 'real_time' leída en el contexto del padre y
        en al menos una de sus branches.

        :return: recordset de product.category activadas
        """
        parents = self.env["res.company"].search([("parent_id", "=", False), ("child_ids", "!=", False)])
        categories = self.with_context(active_test=False).search([])
        activated = self.browse()
        for parent in parents:
            branches = parent._accessible_branches() - parent
            if not branches:
                continue
            for categ in categories:
                if categ.shared_to_branches:
                    continue
                # Automatizada en el padre...
                if categ.with_company(parent).property_valuation != "real_time":
                    continue
                # ...y en al menos una branch.
                if not any(categ.with_company(branch).property_valuation == "real_time" for branch in branches):
                    continue
                # Activar desde el contexto del padre: el write dispara
                # _propagate_valuation_to_branches, que copia costeo/valoración y
                # trae el costo del padre a las branches.
                categ.with_company(parent).shared_to_branches = True
                activated |= categ
        return activated

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
