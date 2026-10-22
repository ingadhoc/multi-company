##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models


class Website(models.Model):
    _inherit = "website"

    @api.ormcache("self.env.uid")
    def _get_cached_companies(self):
        return self.env.user.company_ids.ids
