##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("name", "currency_id", "company_id", "company_id.currency_id")
    def _compute_display_name(self):
        """Append the company suffix and the currency to the journal name.

        Journals whose company has no suffix keep the native name. So do all of them
        when the context asks to show the company (show_company_journal), because
        Odoo already prefixes the company name there and the suffix would repeat it.
        """
        show_company = len(self.env.companies) > 1 and self.env.context.get("show_company_journal")
        native_journals = self.browse()
        for journal in self:
            company = journal.company_id.sudo()
            sufix = company.get_company_sufix()
            if show_company or not sufix:
                native_journals |= journal
                continue
            currency = journal.currency_id or company.currency_id
            journal.display_name = f"{journal.name} ({currency.name}) {sufix}"
        if native_journals:
            super(AccountJournal, native_journals)._compute_display_name()
