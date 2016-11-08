# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


# class account_bank_statement_line(models.Model):
#     _inherit = "account.bank.statement.line"

    # def _domain_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, additional_domain=None, context=None):
    #     domain = super(account_bank_statement_line, self)._domain_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids, str, additional_domain, context)
    #     domain.append(('company_id', '=', st_line.statement_id.company_id.id))
    #     return domain

    # def _domain_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
    #     domain = super(account_bank_statement_line, self)._domain_reconciliation_proposition(cr, uid, st_line, excluded_ids, context)
    #     domain.append(('company_id', '=', st_line.statement_id.company_id.id))
    #     return domain


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    @api.multi
    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        statements = self
        bsl_obj = self.env['account.bank.statement.line']
        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set

        sql_query = """SELECT stl.id 
                        FROM account_bank_statement_line stl  
                        WHERE account_id IS NULL AND not exists (select 1 from account_move m where m.statement_line_id = stl.id)
                            AND company_id = %s
                """
        # CAMBIO!
        # params = (self.env.user.company_id.id,)
        params = (self.journal_id.company_id.id,)
        # FIN CAMBIO!
        if statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statements.ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env['account.bank.statement.line'].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign_partner = [stl.id for stl in st_lines_left if not stl.partner_id]
        refs = list(set([st.name for st in st_lines_left if not stl.partner_id]))
        if st_lines_left and stl_to_assign_partner and refs:
            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = %s 
                                AND aml.partner_id IS NOT NULL) 
                                AND (
                                    (aml.statement_id IS NULL AND aml.account_id IN %s) 
                                    OR 
                                    (acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
                                    )
                                AND aml.ref IN %s
                                """
            params = (self.journal_id.company_id.id, (st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': 0,
        }


# TODO borrar, parece que no esta presente en la v9
# class AccountStatementOperationTemplate(models.Model):
#     _inherit = 'account.statement.operation.template'

#     company_id = fields.Many2one(
#         'res.company', string='Company', related='account_id.company_id',
#         store=True)
