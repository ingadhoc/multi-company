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
        "property_credit_ids",
        "property_credit_limit_ids",
    }

    property_credit_ids = fields.Many2many(
        "res.company.property",
        string="Total Receivables",
        help="Total amount this customer owes you on each company.",
        compute="_compute_properties",
    )
    property_credit_limit_ids = fields.Many2many(
        "res.company.property",
        string="Credit Limits",
        compute="_compute_properties",
    )

    def _compute_properties(self):
        property_fields = dict(
            property_credit_ids="credit",
            property_credit_limit_ids="credit_limit",
        )
        for rec in self:
            company_properties = self.env["res.company.property"].with_context(
                active_model=self._name, active_id=rec.id
            )
            for newfield, oldfield in property_fields.items():
                rec[newfield] = company_properties.with_context(property_field=oldfield)._get_companies()
