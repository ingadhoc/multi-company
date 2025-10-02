# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import psycopg2
from odoo import http
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentPostProcessingInherit(PaymentPostProcessing):
    @http.route("/payment/status/poll", type="jsonrpc", auth="public")
    def poll_status(self, **_kwargs):
        """Fetch the transaction and trigger its post-processing.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # We only poll the payment status if a payment was found, so the transaction should exist.
        monitored_tx = self._get_monitored_transaction()

        # Post-process the transaction before redirecting the user to the landing route and its
        # document.
        if not monitored_tx.is_post_processed:
            try:
                monitored_tx.with_company(monitored_tx.provider_id.journal_id.company_id.id)._post_process()
            except (psycopg2.OperationalError, psycopg2.IntegrityError):  # The database cursor could not be committed.
                request.env.cr.rollback()  # Rollback and try later.
                raise Exception("retry")
            except Exception as e:
                request.env.cr.rollback()
                _logger.exception(
                    "Encountered an error while post-processing transaction with id %s:\n%s", monitored_tx.id, e
                )
                raise

        return {
            "provider_code": monitored_tx.provider_code,
            "state": monitored_tx.state,
            "landing_route": monitored_tx.landing_route,
        }
