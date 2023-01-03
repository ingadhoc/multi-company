# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models



class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(compute=False, inverse='_inverse_journal_id', domain="[('type', 'in', ('bank', 'cash'))]")

    def _inverse_journal_id(self):
        for provider in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', provider.company_id.id),
                ('code', '=', provider.code)
            ], limit=1)
            if provider.journal_id:
                default_payment_method_id = provider._get_default_payment_method_id(
                    provider.code
                )
                existing_payment_method_line = self.env['account.payment.method.line'].search([
                    ('payment_method_id', '=', default_payment_method_id),
                    ('journal_id', '=', provider.journal_id.id)
                ], limit=1)
                if not existing_payment_method_line:
                    self.env['account.payment.method.line'].create({
                        'payment_method_id': default_payment_method_id,
                        'journal_id': provider.journal_id.id,
                    })
            elif payment_method_line:
                payment_method_line.unlink()
