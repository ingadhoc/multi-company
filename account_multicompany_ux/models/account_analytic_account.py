##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountAnalyticAccount(models.Model):

    _inherit = 'account.analytic.account'

    @api.multi
    @api.depends('name', 'partner_id', 'rec.company_id')
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for rec in self:
            name = rec.name
            if rec.code:
                name = '['+rec.code+'] '+name
            if rec.partner_id:
                name = name + ' - ' + rec.partner_id.commercial_partner_id.name
            name = '%s%s' % (name, rec.company_id.get_company_sufix())
            res.append((rec.id, name))
        return res
