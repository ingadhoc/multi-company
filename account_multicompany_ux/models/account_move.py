##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('company_id')
    def check_company(self):
        for move in self:
            if move.company_id.consolidation_company:
                raise ValidationError(_(
                    'You can not create entries on a consolidation company'))

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        """
        We override this method to add filter by companies in the env instead of the company of the user
        For this to work the pr is needed https://github.com/odoo/odoo/pull
        """
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_ids = self.env.companies.ids
            domain = [('company_id', 'in', company_ids), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
