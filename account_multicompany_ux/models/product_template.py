##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_property_context(property_field):
        return (
            "{'active_model': 'product.template', 'active_id': id, "
            "'property_field': '%s'}" % property_field)

    property_account_income_ids = fields.Many2many(
        'res.company.property',
        string="Income Account",
        context=_get_property_context('property_account_income_id'),
        compute='_compute_properties',
    )
    property_account_expense_ids = fields.Many2many(
        'res.company.property',
        string="Expense Account",
        context=_get_property_context('property_account_expense_id'),
        compute='_compute_properties',
    )

    @api.depends()
    def _compute_properties(self):
        company_property = self.env['res.company.property']
        property_fields = dict(
            property_account_income_ids=
            'property_account_income_id',
            property_account_expense_ids=
            'property_account_expense_id',
        )
        for product in self:
            company_properties = company_property.with_context(
                active_model='product.template',
                active_id=self.id)
            values = {}
            for newfield, oldfield in property_fields.items():
                values.update({
                    newfield: company_properties.with_context(
                        property_field=oldfield)._get_companies()
                })
            product.update(values)

    @api.multi
    def action_company_properties(self):
        self.ensure_one()
        return self.env['res.company.property'].with_context(
            active_model='product.template', active_id=self.id
        ).action_company_properties()
