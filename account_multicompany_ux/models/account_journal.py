##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("name", "currency_id", "company_id", "company_id.currency_id")
    def _compute_display_name(self):
        """
        Este método lo que haría es agregar el nombre de la compañía entre paréntesis al final del nombre del diario
        cuando uno ingresa a la vista form esto lo hace en el nombre que está en el menú hamburguesa.
        en caso de que {journal.company_id.get_company_sufix()} sea False llamamos a super para mantener el comportamiento
        nativo de odoo
        """
        for journal in self:
            currency = journal.currency_id or journal.company_id.currency_id
            if journal.company_id.get_company_sufix():
                name = f"{journal.name} ({currency.name}) {journal.company_id.get_company_sufix()}"
                journal.display_name = name
            else:
                super()._compute_display_name()
