# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, _
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    def _get_sales_prices(self, pricelist):
        user_company_id = self.env.user.company_id.id
        return super(ProductTemplate, self.with_company(user_company_id))._get_sales_prices(pricelist)
