from odoo import models, fields

class RepairFee(models.Model):
    _inherit = 'repair.fee'

    tax_id = fields.Many2many(
        'account.tax',
        'repair_fee_line_tax',
        'repair_fee_line_id', 'tax_id',
        'Taxes',
        check_company=False)

    invoice_line_id = fields.Many2one(
        'account.move.line',
        'Invoice Line',
        check_company=False)

class RepairLine(models.Model):
    _inherit = 'repair.line'

    invoice_line_id = fields.Many2one(
        'account.move.line',
        'Invoice Line',
        check_company=False)
