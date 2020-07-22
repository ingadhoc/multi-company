##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields

# TODO remove all this file on v14


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    product_id = fields.Many2one(check_company=True)
    general_account_id = fields.Many2one(domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    move_id = fields.Many2one(check_company=True)


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'
    _check_company_auto = True

    journal_id = fields.Many2one(check_company=True)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    _check_company_auto = True

    account_id = fields.Many2one(
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    statement_id = fields.Many2one(check_company=True)


class AccountJournalGroup(models.Model):
    _inherit = 'account.journal.group'
    _check_company_auto = True

    excluded_journal_ids = fields.Many2many(check_company=True)


class AccountTax(models.Model):
    _inherit = 'account.tax'
    _check_company_auto = True


class AccountTaxRepartitionLine(models.Model):
    _inherit = 'account.tax.repartition.line'
    _check_company_auto = True

    account_id = fields.Many2one(
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), "
        "('internal_type', 'not in', ('receivable', 'payable'))]",
        check_company=True,
    )
    invoice_tax_id = fields.Many2one(check_company=True)
    refund_tax_id = fields.Many2one(check_company=True)


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    _check_company_auto = True

    account_control_ids = fields.Many2many(check_company=True)
    default_credit_account_id = fields.Many2one(
        check_company=True, domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    default_debit_account_id = fields.Many2one(
        check_company=True, domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    profit_account_id = fields.Many2one(check_company=True)
    loss_account_id = fields.Many2one(check_company=True)
    bank_account_id = fields.Many2one(
        check_company=True,
        domain="[('partner_id','=', company_partner_id), '|', "
        "('company_id', '=', False), ('company_id', '=', company_id)]")
    journal_group_ids = fields.Many2many(check_company=True)
    secure_sequence_id = fields.Many2one(check_company=True)


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _check_company_auto = True

    partner_bank_account_id = fields.Many2one(check_company=True)


# No los agregamos porque no se usa mucho y hay que agregar stored de company id que seguro trae conflicto porque
# odoo lo agrega en v14, idem para 'account.fiscal.position.account'
# class AccountFiscalPositionTax(models.Model):
#     _inherit = "account.fiscal.position.tax"
#     _check_company_auto = True


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"
    _check_company_auto = True

    # company_id = fields.Many2one(default=lambda self: self.env.company)
    match_journal_ids = fields.Many2many(
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        check_company=True)
    # company_id = fields.Many2one(default=lambda self: self.env.company)
    account_id = fields.Many2one(
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True)
    journal_id = fields.Many2one(
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        check_company=True)
    tax_ids = fields.Many2many(check_company=True)
    analytic_account_id = fields.Many2one(check_company=True)
    analytic_tag_ids = fields.Many2many(check_company=True)
    second_account_id = fields.Many2one(
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True)
    second_journal_id = fields.Many2one(
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        check_company=True)
    second_tax_ids = fields.Many2many(check_company=True)
    second_analytic_account_id = fields.Many2one(check_company=True)
    second_analytic_tag_ids = fields.Many2many(check_company=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _check_company_auto = True

    move_id = fields.Many2one(check_company=True)
    # company_id = fields.Many2one(default=lambda self: self.env.company)
    account_id = fields.Many2one(
        # da error al installar follow up
        # domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    reconcile_model_id = fields.Many2one(check_company=True)
    payment_id = fields.Many2one(check_company=True)
    tax_ids = fields.Many2many(check_company=True)
    tax_repartition_line_id = fields.Many2one(check_company=True)
    analytic_account_id = fields.Many2one(check_company=True)
    analytic_tag_ids = fields.Many2many(check_company=True)


class AccountAccount(models.Model):
    _inherit = "account.account"
    _check_company_auto = True

    tax_ids = fields.Many2many(check_company=True)
    company_id = fields.Many2one(readonly=True)


class AccountMove(models.Model):
    _inherit = "account.move"
    _check_company_auto = True

    # en realidad dejamos que elija cualquier diario
    # journal_id = fields.Many2one(check_company=True)

    partner_id = fields.Many2one(check_company=True)
    fiscal_position_id = fields.Many2one(check_company=True)
    invoice_payment_term_id = fields.Many2one(check_company=True)
    invoice_partner_bank_id = fields.Many2one(check_company=True)
    invoice_vendor_bill_id = fields.Many2one(check_company=True)
