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
        compute='_get_properties',
    )
    property_account_expense_ids = fields.Many2many(
        'res.company.property',
        string="Expense Account",
        context=_get_property_context('property_account_expense_id'),
        compute='_get_properties',
    )

    @api.one
    def _get_properties(self):
        company_props = self.env['res.company.property'].with_context(
            active_model='product.template', active_id=self.id)
        self.property_account_income_ids = company_props.with_context(
            property_field='property_account_income_id')._get_companies()
        self.property_account_expense_ids = company_props.with_context(
            property_field='property_account_expense_id')._get_companies()

    @api.multi
    def action_company_properties(self):
        self.ensure_one()
        return self.env['res.company.property'].with_context(
            active_model='product.template', active_id=self.id
        ).action_company_properties()
