##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class Website(models.Model):
    _inherit = "website"

    def _create_cart(self):
        sale_order_sudo = super()._create_cart()
        # _sale_get_order_company_fix modifica los valores company related de la orden
        # Durante la creacion de la orden en el website la company siempre debe ser
        # la del website por un Raise en el create(https://github.com/odoo/odoo/blob/18.0/addons/website_sale/models/sale_order.py#L155)
        # por eso creo la orden y luego la modifico
        vals = sale_order_sudo._sale_get_order_company_fix()
        if vals:
            sale_order_sudo.write(vals)
        return sale_order_sudo

    def _get_and_cache_current_fiscal_position(self):
        """Retrieve and cache the current fiscal position, validating company consistency.

        In multi-company scenarios, when a user switches between websites with different
        companies, the cached fiscal position may belong to a different company. This method
        validates that the fiscal position is applicable to the current website sale's company.

        If a fiscal position is cached but belongs to a different company, it is recalculated
        based on the user's partner information and the website sale company context.

        :return: A sudoed fiscal position record valid for the correct company
        :rtype: account.fiscal.position
        """
        fpos = super()._get_and_cache_current_fiscal_position()
        account_fiscal_position_sudo = self.env["account.fiscal.position"].sudo()
        partner = self.env.user.partner_id
        self.ensure_one()

        # Validate that the cached fiscal position belongs to the current website sale's company
        # If it belongs to a different company, recalculate it for the correct company
        if fpos.exists() and fpos.company_id and fpos.company_id != self.company_id:
            fpos = (
                account_fiscal_position_sudo.with_company(self.company_id)._get_fiscal_position(partner)
                or account_fiscal_position_sudo
            )

        return fpos
