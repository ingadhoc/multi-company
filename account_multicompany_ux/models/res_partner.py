##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    property_account_receivable_ids = fields.Many2many(
        'res.company.property',
        string="Account Receivable",
        compute='_compute_properties',
    )
    property_account_payable_ids = fields.Many2many(
        'res.company.property',
        string="Account Payable",
        compute='_compute_properties',
    )
    property_account_position_ids = fields.Many2many(
        'res.company.property',
        string="Fiscal Position",
        compute='_compute_properties',
    )
    property_payment_term_ids = fields.Many2many(
        'res.company.property',
        string='Customer Payment Term',
        compute='_compute_properties',
    )
    property_supplier_payment_term_ids = fields.Many2many(
        'res.company.property',
        string='Supplier Payment Term',
        compute='_compute_properties',
    )
    property_product_pricelist_ids = fields.Many2many(
        'res.company.property',
        string='Sale Pricelist',
        compute='_compute_properties',
    )

    @api.multi
    def _compute_properties(self):
        property_fields = dict(
            property_account_receivable_ids='property_account_receivable_id',
            property_account_payable_ids='property_account_payable_id',
            property_account_position_ids='property_account_position_id',
            property_payment_term_ids='property_payment_term_id',
            property_supplier_payment_term_ids=(
                'property_supplier_payment_term_id'
            ),
            property_product_pricelist_ids='property_product_pricelist',
        )
        for rec in self:
            company_properties = self.env['res.company.property'].with_context(
                active_model=self._name, active_id=rec.id)
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
            active_model=self._name, active_id=self.id
        ).action_company_properties()
