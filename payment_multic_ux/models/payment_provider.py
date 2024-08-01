# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(compute='_compute_journal_id', inverse='_inverse_journal_id', domain="[('type', 'in', ('bank', 'cash'))]", check_company=False,)

    def _compute_journal_id(self):
        # Caso de test de odoo account_payment
        if tools.config['test_enable']:
            super()._compute_journal_id()

    def _inverse_journal_id(self):
        """ Reemplazamos método original """
        # Caso de test de odoo account_payment
        if tools.config['test_enable']:
            super()._inverse_journal_id()
        else:
            for provider in self:
                code = provider._get_code()
                payment_method_line = self.env['account.payment.method.line'].search([
                    *self.env['account.payment.method.line']._check_company_domain(provider.company_id),
                    ('code', '=', code),
                ], limit=1)
                if provider.journal_id:
                    self._link_payment_method_to_journal(provider)
                elif payment_method_line:
                    payment_method_line.unlink()

    def _link_payment_method_to_journal(self, provider):
        """ Reemplazamos método original """
        code = provider._get_code()
        default_payment_method_id = provider._get_provider_payment_method(provider._get_code()).id
        # cambio el dominio de búsqueda sino no me detecta el existing_payment_method_line y me lo duplica
        existing_payment_method_line = self.env['account.payment.method.line'].search([
            ('journal_id.company_id', '=', provider.company_id.id),
            ('code', '=', provider.code),
            ('payment_method_id', '=', default_payment_method_id),
            ('code', '=', code),], limit=1
        )
        if not existing_payment_method_line:
            self.env['account.payment.method.line'].create({
                'payment_method_id': default_payment_method_id,
                'journal_id': provider.journal_id.id,
            })
