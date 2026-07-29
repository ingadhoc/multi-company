from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_branch_stock_root_id(self):
        # Se usa desde el dominio de las reglas de lectura de stock: False deja el
        # dominio en falso, que es lo que corresponde cuando el permiso no aplica.
        self.ensure_one()
        if not self.has_group("stock_account_multicompany_ux.group_stock_all_branches"):
            return False
        return self.env.company.root_id.id
