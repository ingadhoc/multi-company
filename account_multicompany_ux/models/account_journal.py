##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    @api.depends('name', 'currency_id', 'company_id', 'company_id.currency_id')
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            currency = record.currency_id or record.company_id.currency_id
            record_name = '%s (%s)%s' % (
                record.name,
                currency.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res
