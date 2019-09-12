##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """If you have parent/child company, both with taxes "price_include",
        then we should only remove the taxes that are of the current company
        TODO make PR todo odoo
        """
        # at least from subscriptions line_taxes is sent as an empty array
        # TODO we should fix also that case
        if line_taxes:
            prod_taxes = prod_taxes.filtered(
                lambda x: x.company_id in line_taxes.mapped('company_id'))
        return super()._fix_tax_included_price(
            price, prod_taxes, line_taxes)
