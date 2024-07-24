# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(
        compute=False,
        inverse='_inverse_journal_id',
        domain="[('type', 'in', ('bank', 'cash'))]")

