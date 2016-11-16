# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, _
from openerp.addons.account.models.account_invoice import AccountInvoice
from openerp.exceptions import RedirectWarning, except_orm
# from openerp.exceptions import except_orm, Warning, RedirectWarning

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

# This is to solve this issue https://github.com/odoo/odoo/issues/2255


@api.onchange('partner_id', 'company_id')
def _onchange_partner_id(self):
    account_id = False
    payment_term_id = False
    fiscal_position = False
    bank_id = False
    p = self.partner_id
    company_id = self.company_id.id
    type = self.type
    if p:
        partner_id = p.id
        rec_account = p.property_account_receivable_id
        pay_account = p.property_account_payable_id
        if company_id:
            if p.property_account_receivable_id.company_id and \
                    p.property_account_receivable_id.company_id.id != company_id and \
                    p.property_account_payable_id.company_id and \
                    p.property_account_payable_id.company_id.id != company_id:
                prop = self.env['ir.property']
                rec_dom = [('name', '=', 'property_account_receivable_id'), ('company_id', '=', company_id)]
                pay_dom = [('name', '=', 'property_account_payable_id'), ('company_id', '=', company_id)]
                res_dom = [('res_id', '=', 'res.partner,%s' % partner_id)]
                no_res_dom = [('res_id', '=', False)]
                rec_prop = prop.search(
                    rec_dom + res_dom) or prop.search(rec_dom + no_res_dom)
                pay_prop = prop.search(
                    pay_dom + res_dom) or prop.search(pay_dom + no_res_dom)                    
                rec_account = rec_prop.get_by_record(rec_prop)
                pay_account = pay_prop.get_by_record(pay_prop)
                if not rec_account and not pay_account:
                    action = self.env.ref('account.action_account_config')
                    msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                    raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        if type in ('out_invoice', 'out_refund'):
            account_id = rec_account.id
            payment_term_id = p.property_payment_term_id.id
        else:
            account_id = pay_account.id
            payment_term_id = p.property_supplier_payment_term_id.id
        fiscal_position = p.property_account_position_id.id
        bank_id = p.bank_ids and p.bank_ids.ids[0] or False
    self.account_id = account_id
    self.payment_term_id = payment_term_id
    self.fiscal_position_id = fiscal_position

    if type in ('in_invoice', 'in_refund'):
        self.partner_bank_id = bank_id


AccountInvoice._onchange_partner_id = _onchange_partner_id
