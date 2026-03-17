from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Elimina la vista product_template_form_view y product_normal_form_viewpara que Odoo la recree desde el XML,
    evitando un ParseError por campos eliminados en este commit
    (property_account_income_ids / property_account_expense_ids).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    views = env.ref("account_multicompany_ux.product_normal_form_view", raise_if_not_found=False)
    views += env.ref("account_multicompany_ux.product_template_form_view", raise_if_not_found=False)
    if views:
        views.unlink()
