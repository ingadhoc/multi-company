from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def name_get(self):
        """
        Agregamos sufijo cuando en el contexto este la key default_type_tax_use, eso quiere decir que es un lugar
        donde se permiten crear/asociar impuestos, al menos es así en la vista de productos
        """
        res = super().name_get()
        if 'default_type_tax_use' in self._context:
            new_res = []
            for record, res in zip(self, res):
                new_res.append((res[0], '%s%s' % (res[1], record.company_id.get_company_sufix())))
            return new_res
        return res
