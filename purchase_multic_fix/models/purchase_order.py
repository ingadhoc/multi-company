##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains('company_id', 'picking_type_id')
    def check_company(self):
        picking_type_company = self.picking_type_id.warehouse_id.company_id
        if picking_type_company and picking_type_company != self.company_id:
            raise ValidationError(_(
                'The picking type company must be the same as the purchase '
                'order company'))

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        return super(PurchaseOrder, self.with_context(
            force_company=self.company_id.id)).onchange_partner_id()
