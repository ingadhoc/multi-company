##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    @api.multi
    @api.depends('company_id', 'name')
    def name_get(self):
        res = []
        for record in self:
            record_name = '%s%s' % (
                record.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res
