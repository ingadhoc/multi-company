from odoo.addons.website_sale.controllers.main import WebsiteSale



class WebsiteSale(WebsiteSale):

    def values_postprocess(self, order, mode, values, errors, error_msg):     
        new_values, errors, error_msg = super().values_postprocess(order, mode, values, errors, error_msg)
        
        if mode[0] == 'new':
            new_values['company_id'] = False
        return new_values, errors, error_msg
        