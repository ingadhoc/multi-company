##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class ResUsers(models.Model):

    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        """ We inherit this to set the company of the partner user to false if the user
        have more than one companies and the user has multi-company activated"""
        res = super().write(vals)
        group_multi_company = self.env.ref('base.group_multi_company', False)
        if group_multi_company and 'company_ids' in vals:
            self.filtered(
                lambda x: x.id in group_multi_company.users.ids
                and len(x.company_ids) > 1).mapped('partner_id').write(
                {'company_id': False})
        return res
