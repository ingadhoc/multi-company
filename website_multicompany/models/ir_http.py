##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()
        user = request.env.user
        website = request.env['website'].get_current_website()

        # Si el usuario no es el usuario publico las companias allowed son las companias del usuario
        # Esto lo hago para evitar que los usuarios vean todos los registros (sale.order, account.move)
        # en le portal (las alowed_companys se transforman el las companias que filtro en ir.rules)
        if user.id != website._get_cached('user_id'):
            users_company_ids = website._get_cached_companies()
            request.update_context(
                allowed_company_ids=users_company_ids,
            )
        request.website = website.with_context(request.context)
