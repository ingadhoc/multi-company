from odoo import api, SUPERUSER_ID


def _list_providers(env):
    return env['payment.provider'].search([('code', '!=', 'none')]).mapped('code')


def _clear_old_apml(env):
    provider_codes = _list_providers(env)
    if provider_codes:
        env['account.payment.method.line'].search([('payment_provider_id', '=', False), ('code', 'in', provider_codes)]).unlink()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    providers = env['payment.provider'].search([('journal_id', '!=', False)])
    for provider in providers:
        payment_account = provider.journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.code == provider.code).payment_account_id
        provider._inverse_journal_id()
        provider.journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.code == provider.code and x.payment_provider_id.id == provider.id).payment_account_id = payment_account

    _clear_old_apml(env)
