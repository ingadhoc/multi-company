from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(WebsiteSale):
    def _complete_address_values(self, address_values, *args, order_sudo=False, **kwargs):
        super()._complete_address_values(address_values, *args, order_sudo=order_sudo, **kwargs)
        if order_sudo and order_sudo._is_anonymous_cart():
            address_values["company_id"] = False
