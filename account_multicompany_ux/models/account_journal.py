##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    @api.depends('name', 'currency_id', 'company_id', 'company_id.currency_id')
    def _compute_display_name(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance. Este método lo que haría es agregar el nombre de la compañía entre paréntesis al final del nombre del diario cuando uno ingresa a la vista form esto lo hace en el nombre que está en el menú hamburguesa.
        """
        for journal in self:
            currency = journal.currency_id or journal.company_id.currency_id
            name = f"{journal.name} ({currency.name}) {journal.company_id.get_company_sufix()}"
            journal.display_name = name
