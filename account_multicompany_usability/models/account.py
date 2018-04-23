# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            record_name = '%s%s' % (
                record.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.one
    @api.constrains('company_id')
    def check_company(self):
        if self.company_id.consolidation_company:
            raise Warning(
                'You can not create entries on a consolidtion company')


class AccountAnalyticAccount(models.Model):

    _inherit = 'account.analytic.account'

    @api.multi
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            record_name = '%s%s' % (
                super(AccountAnalyticAccount, record).name_get()[0][1],
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res


class AccountAccount(models.Model):

    _inherit = 'account.account'

    @api.multi
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            record_name = '%s%s%s' % (
                record.code and record.code + ' ' or '',
                record.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    @api.multi
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            currency = record.currency_id or record.company_id.currency_id
            record_name = '%s (%s)%s' % (
                record.name,
                currency.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def name_get(self):
        """
        No llamamos a super porque tendriamos que igualmente hacer un read
        para obtener la compania y no queremos disminuir la performance
        """
        res = []
        for record in self:
            record_name = '%s%s' % (
                record.description or record.name,
                record.company_id.get_company_sufix())
            res.append((record.id, record_name))
        return res
