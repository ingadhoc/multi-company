##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.constrains('company_id', 'warehouse_id')
    def check_company(self):
        for rec in self:
            warehouse_id_company = rec.warehouse_id.company_id
            if warehouse_id_company and warehouse_id_company != rec.company_id:
                raise ValidationError(_(
                    'The warehouse company must be the same as the sale '
                    'order company'))
