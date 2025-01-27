from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _compute_display_name(self):
        """
        Agregamos sufijo de compañía en reportes financieros si hay más de una compañía seleccionada
        """
        if self._context.get("report_id") and len(self._context.get("company_ids", self.env.companies.ids)) > 1:
            for account in self:
                if account.code:
                    company = self.env["res.company"].browse(self._context["allowed_company_ids"][0])
                    account.display_name = (
                        f"{account.with_company(company).code} {account.name}{company.get_company_sufix()}"
                    )
                else:
                    account.display_name = account.name
        else:
            super()._compute_display_name()
