##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountAccount(models.Model):

    _inherit = 'account.account'

    @api.multi
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            record_name = '%s%s%s' % (
                record.code and record.code + ' ' or '',
                record.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res
