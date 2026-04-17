##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.ondelete(at_uninstall=False)
    def _unlink_move_lines(self):
        move_ids = self.mapped("move_id").ids
        if not move_ids:
            return self.env["sale.order.line"]
        sale_lines = self.env["sale.order.line"].sudo().search([("invoice_lines.move_id", "in", move_ids)])
        if sale_lines and not (self.env.su or sale_lines.with_user(self.env.user).has_access("write")):
            raise ValidationError(
                self.env._("You cannot delete invoice lines related to sale orders you do not have access to.")
            )

    def write(self, vals):
        if "quantity" in vals:
            draft_lines = self.filtered(lambda l: l.move_id.state == "draft")
            if draft_lines:
                sale_lines = self.env["sale.order.line"].sudo().search([("invoice_lines", "in", draft_lines.ids)])
                if sale_lines and not (self.env.su or sale_lines.with_user(self.env.user).has_access("write")):
                    raise ValidationError(
                        self.env._(
                            "You cannot change the quantity of invoice lines related to sale orders you do not have access to."
                        )
                    )
        return super().write(vals)
