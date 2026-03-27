##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.ondelete(at_uninstall=False)
    def _unlink_move_lines(self):
        move_ids = self.mapped("move_id").ids
        if not move_ids:
            return self.env["sale.order.line"]
        sale_lines = self.env["sale.order.line"].sudo().search([("invoice_lines.move_id", "in", move_ids)])
        if sale_lines and not sale_lines.with_user(self.env.user).has_access("write"):
            raise ValidationError(
                _("No puede eliminar lineas de factura relacionadas con ordenes de venta a las que no tiene acceso.")
            )
