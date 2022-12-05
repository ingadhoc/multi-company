from odoo import api, models


class AccountAccount(models.Model):

    _inherit = 'account.account'

    def name_get(self):
        """
        Agregamos sufijo de compañía en reportes financieros si hay más de una compañía seleccionada
        """
        res = super().name_get()
        if self._context.get('report_id') and len(self._context.get('company_ids', self.env.companies.ids)) > 1:
            new_res = []
            for record, res in zip(self, res):
                new_res.append((res[0], '%s%s' % (res[1], record.company_id.get_company_sufix())))
            return new_res
        return res
