##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # TODO. this should go in a PR to ODOO
    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        fiscal_position = self.env[
            'account.fiscal.position'].with_context(
                force_company=self.company_id.id).get_fiscal_position(
                self.partner_id.id, self.partner_shipping_id.id)
        if fiscal_position:
            self.fiscal_position_id = fiscal_position
