from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _create_payment(self, **extra_create_values):
        # Add force_company to catch later in the account.payment creation.  
        return super(PaymentTransaction, self.with_context(force_company_id = self.provider_id.journal_id.company_id.id))._create_payment(**extra_create_values)