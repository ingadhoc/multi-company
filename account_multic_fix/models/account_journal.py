##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def action_create_new(self):
        # we fix that if we call create invoice from dashboard of a journal
        # of a child company, user company is set
        self = self.with_context(default_company_id=self.company_id.id)
        return super().action_create_new()
