##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    short_name = fields.Char(
        help='Short name used to identify this company',
    )

    consolidation_company = fields.Boolean(
        help='Journal entries are not allowed on consolidation companies. (so'
        ' invoices, payments, etc neither)'
    )

    @api.multi
    def get_company_sufix(self):
        """ Cuando pedimos para unr registro que no tiene cia no queremos que
        ensure_one arroje error
        """
        condition =  \
            len(self) != 1 or \
            self._context.get('no_company_sufix') or \
            not self.env.user.has_group('base.group_multi_company')

        return '' if condition else ' (%s)' % (self.short_name or self.name)
