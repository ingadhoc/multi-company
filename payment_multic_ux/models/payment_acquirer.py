# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models



class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    journal_id = fields.Many2one(compute=False, inverse='_inverse_journal_id', domain="[('type', 'in', ['bank', 'cash'])]")

    def _inverse_journal_id(self):
        for acquirer in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if acquirer.journal_id:
                default_payment_method_id = acquirer._get_default_payment_method_id()
                existing_payment_method_line = self.env['account.payment.method.line'].search([
                    ('payment_method_id', '=', default_payment_method_id),
                    ('journal_id', '=', acquirer.journal_id.id)
                ], limit=1)
                if not existing_payment_method_line:
                    self.env['account.payment.method.line'].create({
                        'payment_method_id': default_payment_method_id,
                        'journal_id': acquirer.journal_id.id,
                    })
            elif payment_method_line:
                payment_method_line.unlink()
