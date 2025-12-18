##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    company_id = fields.Many2one(tracking=True)

    company_can_change = fields.Boolean(
        compute="_compute_company_can_change",
        help="True if the company has no branches and is not a branch",
    )

    @api.depends("company_id", "company_id.parent_id", "company_id.child_ids")
    def _compute_company_can_change(self):
        for move in self:
            # Can change company if the company has no branches and is not a branch
            move.company_can_change = move.company_id.parent_id or move.company_id.child_ids

    @api.constrains("company_id")
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(_("You can not create entries on a consolidation company"))
