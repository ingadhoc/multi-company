from odoo.addons.website_sale.controllers.main import WebsiteSale



class WebsiteSale(WebsiteSale):

    def _complete_address_values(
        self, address_values, address_type, use_delivery_as_billing, order_sudo
    ):
        super()._complete_address_values(address_values, address_type, use_delivery_as_billing, order_sudo)
        if not address_values['user_id']:
            address_values['company_id'] = False
