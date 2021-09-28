##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
from odoo import tools


class ResCompany(models.Model):

    _inherit = 'res.company'

    short_name = fields.Char(
        help='Short name used to identify this company',
    )

    consolidation_company = fields.Boolean(
        help='Journal entries are not allowed on consolidation companies. (so'
        ' invoices, payments, etc neither)'
    )

    # TODO habria que terminar de ver si esta bien este cache o en realidad para
    # ser mas performante no hay que usar nada de self
    @tools.ormcache_context('self.env.uid', 'self.name', 'self.short_name', keys=('no_company_sufix',))
    def get_company_sufix(self):
        """ Cuando pedimos para un registro que no tiene cia no queremos que
        ensure_one arroje error
        """
        condition =  \
            len(self) != 1 or \
            self._context.get('no_company_sufix') or \
            not self.env.user.has_group('base.group_multi_company')

        return '' if condition else ' (%s)' % (self.short_name or self.name)
