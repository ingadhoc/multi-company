from odoo import models
from odoo.exceptions import UserError


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    def reconcile(self):
        for wizard in self:
            companies = wizard.move_line_ids.mapped("company_id")
            if len(companies) > 1 and companies.filtered(lambda c: c.child_ids and c.block_intercompany_conciliation):
                raise UserError(
                    "Cannot reconcile journal items from different companies. "
                    "Please verify that the 'Block inter-company reconciliation' option "
                    "is not enabled in the settings of the companies involved."
                )
        return super().reconcile()
