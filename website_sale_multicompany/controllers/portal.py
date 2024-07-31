
import urllib.parse

import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.payment.controllers import portal
from odoo.exceptions import AccessError, MissingError, ValidationError

class PaymentPortal(portal.PaymentPortal):

    @http.route()
    def payment_method(self, **kwargs):
        """ Remplazo el metodo del controlador de odoo porque la compañia de esta url es siempre la
        del website y necesitamos que sea la del usuario o la de la subscricion que vamos a pagar.
        """
        partner_sudo = request.env.user.partner_id  # env.user is always sudoed

        if 'sale_order_id' in kwargs and 'access_token' in kwargs:
            try:
                order_sudo = self._document_check_access('sale.order', int(kwargs.get('sale_order_id')), access_token=kwargs.get('access_token'))
                company_id = order_sudo.company_id
            except (AccessError, MissingError):
                company_id = request.env.user.company_id

        else:
            company_id = request.env.user.company_id
        # Select all the payment methods and tokens that match the payment context.
        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            company_id.id,
            partner_sudo.id,
            0.,  # There is no amount to pay with validation transactions.
            force_tokenization=True,
            is_validation=True,
            **kwargs,
        )  # In sudo mode to read the fields of providers and partner (if logged out).
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner_sudo.id,
            force_tokenization=True,
        )  # In sudo mode to read the fields of providers.
        tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
            None, partner_sudo.id, is_validation=True
        )  # In sudo mode to read the commercial partner's and providers' fields.

        access_token = payment_utils.generate_access_token(partner_sudo.id, None, None)

        payment_form_values = {
            'mode': 'validation',
            'allow_token_selection': False,
            'allow_token_deletion': True,
        }
        payment_context = {
            'reference_prefix': payment_utils.singularize_reference_prefix(prefix='V'),
            'partner_id': partner_sudo.id,
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'transaction_route': '/payment/transaction',
            'landing_route': '/my/payment_method',
            'access_token': access_token,
        }
        rendering_context = {
            **payment_form_values,
            **payment_context,
            **self._get_extra_payment_form_values(**kwargs),
        }
        return request.render('payment.payment_methods', rendering_context)
