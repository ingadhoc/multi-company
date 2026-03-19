from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _compute_display_name(self):
        """
        Agregamos sufijo de compañía en reportes financieros si hay más de una compañía seleccionada
        """
        if self.env.context.get("report_id") and len(self.env.context.get("company_ids", self.env.companies.ids)) > 1:
            for account in self:
                if account.code:
                    if len(account.company_ids) > 1:
                        to_show_company = self._context["allowed_company_ids"][0]
                    else:
                        to_show_company = account.company_ids.id

                    company = self.env["res.company"].browse(to_show_company)
                    account.display_name = (
                        f"{account.with_company(company).code} {account.name}{company.get_company_sufix()}"
                    )
                else:
                    account.display_name = account.name
        else:
            super()._compute_display_name()
