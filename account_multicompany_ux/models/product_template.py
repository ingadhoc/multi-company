##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "res.company.property.mixin"]
    _property_fields = {"standard_price_ids"}

    standard_price_ids = fields.Many2many(
        "res.company.property",
        string="Costs",
        compute="_compute_properties",
    )

    @api.depends()
    def _compute_properties(self):
        company_property = self.env["res.company.property"]
        for rec in self:
            company_properties = company_property.with_context(active_model="product.template", active_id=rec.id)
            rec.standard_price_ids = company_properties.with_context(property_field="standard_price")._get_companies()
