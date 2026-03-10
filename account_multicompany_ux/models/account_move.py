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

    def _compute_company_id(self):
        """When the active company is a branch and the selected journal belongs to
        a parent company (shared to branches), Odoo's native logic calls
        `journal.company_id._accessible_branches()[:1]` which traverses the
        tree top-down and returns the parent first, wrongly setting the invoice
        company to the parent instead of the branch.

        We override this so that when env.company is a branch and the journal's
        company is an ancestor of env.company (i.e. a shared journal), we keep
        env.company (the branch) as the invoice company.
        """
        for move in self:
            if move.journal_id.company_id not in move.company_id.parent_ids:
                journal_company = move.journal_id.company_id or self.env.company
                current_company = self.env.company
                # If the journal's company is an ancestor of the current branch
                # (shared journal), keep the branch as the invoice company.
                if current_company.parent_id and current_company in journal_company._accessible_branches():
                    move.company_id = current_company
                else:
                    move.company_id = journal_company._accessible_branches()[:1]

    @api.constrains("company_id")
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(_("You can not create entries on a consolidation company"))
