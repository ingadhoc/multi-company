##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains('company_id', 'warehouse_id')
    def check_company(self):
        """ Esta constraint, además de arreglar esta inconsistencia de manera
        voluntaria tambien arregla, por ejemplo, lo que si podría producir
        si se configura website en cia hija y admin tiene cia padre, en ese
        caso, desde ecommerce, no se encuentra warehouse pero se intenta
        crear venta en cia hija y admin obtiene valor por defecto de warehouse
        para cia padre
        """
        if any(self.filtered(
                lambda s: s.warehouse_id and s.warehouse_id.company_id !=
                s.company_id)):
            raise ValidationError(_(
                'The warehouse company must be the same as the sale '
                'order company'))
