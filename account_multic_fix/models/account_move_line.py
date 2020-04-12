##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_account(self):
        if not self._context.get('force_company'):
            self = self.with_context(force_company=self.company_id.id or self.move_id.company_id.id)
        return super(AccountMoveLine, self)._get_computed_account()
