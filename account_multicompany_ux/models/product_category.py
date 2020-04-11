##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ProductCategory(models.Model):

    _inherit = 'product.category'

    property_account_income_categ_ids = fields.Many2many(
        'res.company.property',
        string="Income Accounts",
        compute='_compute_properties',
    )
    property_account_expense_categ_ids = fields.Many2many(
        'res.company.property',
        string="Expense Accounts",
        compute='_compute_properties',
    )

    @api.depends()
    def _compute_properties(self):
        company_property = self.env['res.company.property']
        property_fields = dict(
            property_account_income_categ_ids=(
                'property_account_income_categ_id'),
            property_account_expense_categ_ids=(
                'property_account_expense_categ_id'),
        )

        for rec in self:
            company_properties = company_property.with_context(
                active_model=self._name,
                active_id=rec.id)
            for newfield, oldfield in property_fields.items():
                rec[newfield] = company_properties.with_context(
                    property_field=oldfield)._get_companies()

    def action_company_properties(self):
        self.ensure_one()
        return self.env['res.company.property'].with_context(
            active_model=self._name, active_id=self.id
        ).action_company_properties()
