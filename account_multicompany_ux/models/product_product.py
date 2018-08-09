##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ProductProduct(models.Model):
    """Overwrite of computed fields using product_tmpl_id instead of id"""

    _inherit = 'product.product'

    property_account_income_ids = fields.Many2many(
        'res.company.property',
        string="Income Account",
        compute='_compute_properties',
    )
    property_account_expense_ids = fields.Many2many(
        'res.company.property',
        string="Expense Account",
        compute='_compute_properties',
    )

    @api.depends()
    def _compute_properties(self):
        company_property = self.env['res.company.property']
        property_fields = dict(
            property_account_income_ids='property_account_income_id',
            property_account_expense_ids='property_account_expense_id',
        )
        for rec in self:
            company_properties = company_property.with_context(
                active_model='product.template',
                active_id=rec.product_tmpl_id.id)
            values = {}
            for newfield, oldfield in property_fields.items():
                values.update({
                    newfield: company_properties.with_context(
                        property_field=oldfield)._get_companies()
                })
            rec.update(values)

    @api.multi
    def action_company_properties(self):
        self.ensure_one()
        return self.env['res.company.property'].with_context(
            active_model='product.template', active_id=self.product_tmpl_id.id
        ).action_company_properties()
