##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    reversed_entry_id = fields.Many2one(check_company=False)
    company_id = fields.Many2one(tracking=True)

    @api.constrains("company_id")
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(self.env._("You can not create entries on a consolidation company"))

    def _reverse_moves(self, default_values_list=None, cancel=False):
        sale_lines = self.env["sale.order.line"].sudo().search([("invoice_lines.move_id", "in", self.ids)])
        if sale_lines and not sale_lines.with_user(self.env.user).has_access("write"):
            raise ValidationError(
                self.env._(
                    "You cannot create a credit note for invoices related to sale orders you do not have access to."
                )
            )
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
