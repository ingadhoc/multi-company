##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

<<<<<<< 509f02de86da983fc943f3b74e0aed4826bc3f38
    def _reconcile_plan(self, reconciliation_plan):
        if self.env.context.get("skip_cross_company_reversal_reconcile"):
            reconciliation_plan = self._filter_cross_company_reversal_plan(reconciliation_plan)
        return super()._reconcile_plan(reconciliation_plan)

    @api.model
    def _filter_cross_company_reversal_plan(self, plan):
        filtered_plan = []
        for item in plan:
            if isinstance(item, list):
                filtered_plan.append(self._filter_cross_company_reversal_plan(item))
                continue
            moves = item.move_id
            if len(moves.company_id) > 1 and any(move.reversed_entry_id in moves for move in moves):
                continue
            filtered_plan.append(item)
        return filtered_plan

||||||| 917d9a1d9a744a187cdd50a8a235079e313c4a1d
=======
    def _get_analytic_distribution_arguments(self, root_plans):
        # the account code is company dependent and stored on the company root, so reading it
        # from another root returns it empty and no distribution model matches the prefix
        arguments = super()._get_analytic_distribution_arguments(root_plans)
        if self.company_id:
            arguments["account_prefix"] = self.account_id.with_company(self.company_id).code
        return arguments

>>>>>>> f338d3b08a15206e309fbe19565c2634a6e95776
    @api.ondelete(at_uninstall=False)
    def _unlink_move_lines(self):
        # at_uninstall=False only skips this check when this module is uninstalled:
        # uninstalling another module that deletes move lines runs with the user env
        # (not as superuser), so a settings admin without sales access would abort it
        if self.pool.uninstalling_modules:
            return
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
