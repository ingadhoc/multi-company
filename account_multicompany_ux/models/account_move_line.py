##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    # NOTE This is an exact copy of odoo get_data_for_manual_reconciliation
    # method, since is not easy inherit we copy and paste just to change some
    # lines in order to make it work multi company
    @api.model
    def _add_company_name_to_rows(self, rows):
        for row in rows:
            if 'account_code' in row:
                row['account_code'] = '%s%s' % (
                    row['account_code'], self.env['account.account'].browse(
                        row['account_id']).company_id.get_company_sufix())
        return True

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None,
                                           account_type=None):
        # Code is the same as original method, but we use it to compute for
        # the child_companies
        prev_rows = super(
            AccountMoveLine, self).get_data_for_manual_reconciliation(
            res_type, res_ids, account_type)
        self._add_company_name_to_rows(prev_rows)
        child_companies = self.env.user.company_id.child_ids
        if not child_companies:
            return prev_rows

        if res_ids is not None and len(res_ids) == 0:
            return []
        res_ids = res_ids and tuple(res_ids)

        assert res_type in ('partner', 'account')
        assert account_type in ('payable', 'receivable', None)
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'
        child_company_ids = child_companies and tuple(child_companies.ids)
        # pylint: disable=E8103
        query = ("""
            SELECT {0} account_id, account_name, account_code, max_date,
                   to_char(last_time_entries_checked, 'YYYY-MM-DD')
                   AS last_time_entries_checked
            FROM (
                    SELECT {1}
                        {res_alias}.last_time_entries_checked
                        AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a
                        ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at
                        ON (at.id = a.user_type_id)
                        {2}
                    WHERE
                        a.reconcile IS TRUE
                        AND l.full_reconcile_id is NULL
                        {3}
                        {4}
                        {5}
                        AND l.company_id in {6}
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual < 0
                        )
                    GROUP BY {8} a.id, a.name, a.code,
                    {res_alias}.last_time_entries_checked
                    ORDER BY {res_alias}.last_time_entries_checked
                ) as s
            WHERE (last_time_entries_checked IS NULL
            OR max_date > last_time_entries_checked)
        """.format(
            is_partner and 'partner_id, partner_name,' or ' ',
            is_partner and 'p.id AS partner_id, p.name '
                           'AS partner_name,' or ' ',
            is_partner and 'RIGHT JOIN res_partner p '
                           'ON (l.partner_id = p.id)' or ' ',
            is_partner and ' ' or "AND at.type <> 'payable' "
                                  "AND at.type <> 'receivable'",
            account_type and "AND at.type = %(account_type)s" or '',
            res_ids and 'AND ' + res_alias + '.id in %(res_ids)s' or '',
            child_company_ids and '%(child_company_ids)s' or '',
            is_partner and 'AND l.partner_id = p.id' or ' ',
            is_partner and 'l.partner_id, p.id,' or ' ',
            res_alias=res_alias
        ))
        self.env.cr.execute(query, locals())

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(self.env['account.account'].browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(self.env['res.partner'].browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = self.env['account.account'].browse(row['account_id'])
            row['currency_id'] = account.currency_id.id or account. \
                company_id.currency_id.id
            partner_id = is_partner and row['partner_id'] or None
            row['reconciliation_proposition'] = \
                self.get_reconciliation_proposition(account.id, partner_id)
        self._add_company_name_to_rows(rows)
        total_rows = rows + prev_rows
        return total_rows

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(
            self, target_currency=False, target_date=False):
        ret = super(AccountMoveLine, self). \
            prepare_move_lines_for_reconciliation_widget(
            target_currency=target_currency, target_date=target_date)
        for ret_line in ret:
            for line in self:
                if ret_line['id'] == line.id:
                    ret_line['company_id'] = line.company_id.id
        return ret
