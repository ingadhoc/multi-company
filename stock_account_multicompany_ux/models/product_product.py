from odoo import api, fields, models


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
        string="Cost",
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
                is_branch and product.categ_id.with_company(root_company).shared_to_branches
            )

    @api.depends_context("company")
    @api.depends("standard_price", "categ_id.shared_to_branches")
    def _compute_parent_standard_price(self):
        root_company = self.env.company.root_id
        for product in self:
            if product.is_cost_shared_from_parent:
                product.parent_standard_price = product.with_company(root_company).standard_price
            else:
                product.parent_standard_price = product.standard_price
