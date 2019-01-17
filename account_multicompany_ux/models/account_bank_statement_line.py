##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
# flake8: noqa
from odoo import api, models
from odoo.tools import float_repr, float_round


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    # NOTE This is an exact copy of odoo get_reconciliation_proposition
    # method, since is not easy inherit we copy and paste just to change some
    # lines in order to make it work multi company
    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line
            Note: it only looks for move lines in the same currency as the statement line.
        """
        self.ensure_one()
        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        # THIS IS NEW CHANGE
        # params = {'company_id': self.env.user.company_id.id,
        params = {'company_id': self.company_id.id,
                    'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
                    'amount': float_repr(float_round(amount, precision_digits=precision), precision_digits=precision),
                    'partner_id': self.partner_id.id,
                    'excluded_ids': tuple(excluded_ids),
                    'ref': self.name,
                    }
        # Look for structured communication match
        if self.name:
            add_to_select = ", CASE WHEN aml.ref = %(ref)s THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = self._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            sql_query += " AND (aml.ref= %(ref)s or m.name = %(ref)s) \
                    ORDER BY temp_field_order, date_maturity desc, aml.id desc"
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Look for a single move line with the same amount
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' or 'abs(%(amount)s::numeric)'
        sql_query = self._get_common_sql_query(excluded_ids=excluded_ids) + \
                " AND ("+field+" = %(amount)s::numeric OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = " + liquidity_amt_clause + ")) \
                ORDER BY date_maturity desc, aml.id desc LIMIT 1"
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchone()
        if results:
            return self.env['account.move.line'].browse(results[0])

        return self.env['account.move.line']

    @api.multi
    def auto_reconcile(self):
        """ Try to automatically reconcile the statement.line ; return the counterpart journal entry/ies if the automatic reconciliation succeeded, False otherwise.
            TODO : this method could be greatly improved and made extensible
        """
        self.ensure_one()
        match_recs = self.env['account.move.line']

        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        # THIS IS NEW CHANGE
        # params = {'company_id': self.env.user.company_id.id,
        params = {'company_id': self.company_id.id,
                    'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
                    'amount': float_round(amount, precision_digits=precision),
                    'partner_id': self.partner_id.id,
                    'ref': self.name,
                    }
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        # Look for structured communication match
        if self.name:
            sql_query = self._get_common_sql_query() + \
                " AND aml.ref = %(ref)s AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # Look for a single move line with the same partner, the same amount
        if not match_recs:
            if self.partner_id:
                sql_query = self._get_common_sql_query() + \
                " AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
                self.env.cr.execute(sql_query, params)
                match_recs = self.env.cr.dictfetchall()
                if len(match_recs) > 1:
                    return False

        if not match_recs:
            return False

        match_recs = self.env['account.move.line'].browse([aml.get('id') for aml in match_recs])
        # Now reconcile
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for aml in match_recs:
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        try:
            with self._cr.savepoint():
                counterpart = self.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec)
            return counterpart
        except UserError:
            # A configuration / business logic error that makes it impossible to auto-reconcile should not be raised
            # since automatic reconciliation is just an amenity and the user will get the same exception when manually
            # reconciling. Other types of exception are (hopefully) programmation errors and should cause a stacktrace.
            self.invalidate_cache()
            self.env['account.move'].invalidate_cache()
            self.env['account.move.line'].invalidate_cache()
            return False

    def get_move_lines_for_reconciliation(
            self, partner_id=None, excluded_ids=None, str=False,
            offset=0, limit=None, additional_domain=None,
            overlook_partner=False):
        res = super(AccountBankStatementLine,
                    self).get_move_lines_for_reconciliation(
            partner_id=partner_id, excluded_ids=excluded_ids, str=str,
            offset=offset, limit=limit, additional_domain=additional_domain,
            overlook_partner=overlook_partner)
        return res.filtered(lambda x: x.company_id == self.company_id)

    def get_statement_line_for_reconciliation_widget(self):
        data = super(AccountBankStatementLine, self). \
            get_statement_line_for_reconciliation_widget()
        if self.amount_currency and self.currency_id:
            amount = self.amount_currency
        else:
            amount = self.amount
        data['company_id'] = self.company_id.id
        if self.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = \
                    self.partner_id.with_context(
                        force_company=self.company_id.id
                    ).property_account_receivable_id.id
            else:
                data['open_balance_account_id'] = \
                    self.partner_id.with_context(
                        force_company=self.company_id.id
                    ).property_account_payable_id.id
        return data

    def _prepare_reconciliation_move(self, move_ref):
        result = super()._prepare_reconciliation_move(move_ref)
        result['company_id'] = self.statement_id.company_id.id
        return result
