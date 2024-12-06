##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
from odoo import models, tools
from odoo.http import request


class Website(models.Model):

    _inherit = 'website'

    def sale_get_order(self, force_create=False):
        sale_order_sudo = super().sale_get_order(force_create)
        # _sale_get_order_company_fix modifica los valores company related de la orden
        # Durante la creacion de la orden en el website la company siempre debe ser
        # la del website por un Raise en el create(https://github.com/odoo/odoo/blob/18.0/addons/website_sale/models/sale_order.py#L155)
        # por eso creo la orden y luego la modifico
        vals = sale_order_sudo._sale_get_order_company_fix()
        if vals:
            sale_order_sudo.write(vals)
        return sale_order_sudo
