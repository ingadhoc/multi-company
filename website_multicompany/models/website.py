##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, tools


class Website(models.Model):

    _inherit = 'website'

    @tools.ormcache('self.env.uid')
    def _get_cached_companies(self):
        return self.env.user.company_ids.ids
