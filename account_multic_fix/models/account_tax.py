# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """If you have parent/child company, both with taxes "price_include",
        then we should only remove the taxes that are of the current company
        TODO make PR todo odoo
        """
        prod_taxes = prod_taxes.filtered(
            lambda x: x.company_id in line_taxes.mapped('company_id'))
        return super(AccountTax, self)._fix_tax_included_price(
            price, prod_taxes, line_taxes)
