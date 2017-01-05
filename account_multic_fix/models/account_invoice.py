# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def create(self, vals):
        """
        Fix that if we create an invoice from parent company of child company
        company must be set as the one from the journal
        """
        company_id = vals.get('company_id')
        journal_id = vals.get('journal_id')
        if journal_id and not company_id:
            vals['company_id'] = self.env['account.journal'].browse(
                journal_id).company_id.id
        return super(AccountInvoice, self).create(vals)

    fiscal_position_id = fields.Many2one(
        domain="['|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]"
    )

    @api.one
    @api.constrains('fiscal_position_id', 'company_id')
    def _check_fiscal_position_company(self):
        position_company = self.fiscal_position_id.company_id
        if position_company and position_company != self.company_id:
            raise ValidationError(_(
                'The company of the invoice and from the fiscal position must'
                ' be the same!'))
