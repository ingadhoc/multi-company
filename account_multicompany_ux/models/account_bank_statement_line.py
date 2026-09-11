##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    partner_id_domain = fields.Json(
        compute="_compute_partner_id_domain",
        exportable=False,
    )

    @api.depends("company_id")
    @api.depends_context("allowed_company_ids")
    def _compute_partner_id_domain(self):
        for line in self:
            company = line.company_id or self.env.company
            company_domain = self.env["res.partner"]._check_company_domain(company)
            # Preserve the original partner-type filter: only top-level contacts
            # (companies or individuals that are not child contacts).
            line.partner_id_domain = company_domain + [
                "|",
                ("parent_id", "=", False),
                ("is_company", "=", True),
            ]
