from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Espejo a nivel template de la lógica de product.product: parado en una
    branch, expone el costo (standard_price) de la compañía raíz del grupo
    cuando la categoría está marcada como 'shared_to_branches'.

    El form de producto (y el de variante, que lo hereda) muestra el costo del
    template; por eso los campos auxiliares se replican acá para que la vista
    pueda hacer el swap de solo lectura sin tocar standard_price ni la valoración.
    """

    _inherit = "product.template"

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
        for template in self:
            template.is_cost_shared_from_parent = (
                is_branch and template.categ_id.with_company(root_company).shared_to_branches
            )

    @api.depends_context("company")
    @api.depends("standard_price", "categ_id.shared_to_branches")
    def _compute_parent_standard_price(self):
        root_company = self.env.company.root_id
        for template in self:
            if template.is_cost_shared_from_parent:
                template.parent_standard_price = template.with_company(root_company).standard_price
            else:
                template.parent_standard_price = template.standard_price
