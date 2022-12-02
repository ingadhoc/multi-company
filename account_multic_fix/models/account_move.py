##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"



    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        # we override this method to add filter by companies in the env instead of the company of the user
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_ids = self.env.companies.ids
            domain = [('company_id', 'in', company_ids), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
