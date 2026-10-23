from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_branch_stock_root_ids(self, company_ids):
        # Used from the domain of the stock read rules: an empty list leaves the domain
        # false, which is what we want when the permission does not apply. The roots come
        # from every company active in the switcher (company_ids of the rule context):
        # env.company is only the first one, so with active companies of two trees the
        # stock of the other tree was left out.
        self.ensure_one()
        if not self.has_group("stock_account_multicompany_ux.group_stock_all_branches"):
            return []
        return self.env["res.company"].sudo().browse(company_ids).root_id.ids
