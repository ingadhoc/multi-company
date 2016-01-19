# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class account_invoice_report(models.Model):
    _inherit = 'account.invoice.report'

    active = fields.Boolean('Active')

    _depends = {
        'account.invoice': ['active'],
    }

    def _select(self):
        return super(
            account_invoice_report, self)._select() + ", sub.active as active"

    def _sub_select(self):
        return super(
            account_invoice_report, self)._sub_select() + ", ai.active as active"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.active"
