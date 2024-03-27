from odoo import api, models


class AccountAccount(models.Model):

    _inherit = 'account.account'

    def _compute_display_name(self):
        """
        Agregamos sufijo de compañía en reportes financieros si hay más de una compañía seleccionada
        """
        if self._context.get('report_id') and len(self._context.get('company_ids', self.env.companies.ids)) > 1:
            for account in self:
                account.display_name = f"{account.code} {account.name}{account.company_id.get_company_sufix()}"
        else:
            super()._compute_display_name()
