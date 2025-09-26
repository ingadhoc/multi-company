##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "res.company.property.mixin"]
    _property_fields = {
        "property_account_receivable_ids",
        "property_account_payable_ids",
        "property_account_position_ids",
        "property_payment_term_ids",
        "property_supplier_payment_term_ids",
        "property_product_pricelist_ids",
        "property_credit_ids",
    }

    property_account_receivable_ids = fields.Many2many(
        "res.company.property",
        string="Accounts Receivable",
        compute="_compute_properties",
    )
    property_account_payable_ids = fields.Many2many(
        "res.company.property",
        string="Accounts Payable",
        compute="_compute_properties",
    )
    property_account_position_ids = fields.Many2many(
        "res.company.property",
        string="Fiscal Positions",
        compute="_compute_properties",
    )
    property_payment_term_ids = fields.Many2many(
        "res.company.property",
        string="Customer Payment Term",
        compute="_compute_properties",
    )
    property_supplier_payment_term_ids = fields.Many2many(
        "res.company.property",
        string="Supplier Payment Terms",
        compute="_compute_properties",
    )
    property_product_pricelist_ids = fields.Many2many(
        "res.company.property",
        string="Sale Pricelists",
        compute="_compute_properties",
    )

    property_credit_ids = fields.Many2many(
        "res.company.property",
        string="Credit",
        compute="_compute_properties",
    )

    def _compute_properties(self):
        property_fields = dict(
            property_account_receivable_ids="property_account_receivable_id",
            property_account_payable_ids="property_account_payable_id",
            property_account_position_ids="property_account_position_id",
            property_payment_term_ids="property_payment_term_id",
            property_supplier_payment_term_ids=("property_supplier_payment_term_id"),
            property_product_pricelist_ids="property_product_pricelist",
            property_credit_ids="credit",
        )
        for rec in self:
            company_properties = self.env["res.company.property"].with_context(
                active_model=self._name, active_id=rec.id
            )
            for newfield, oldfield in property_fields.items():
                rec[newfield] = company_properties.with_context(property_field=oldfield)._get_companies()
