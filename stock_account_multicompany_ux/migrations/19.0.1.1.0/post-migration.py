from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """
    Repobla shared_to_branches (ahora company_dependent / jsonb) a partir de las
    categorías que estaban compartidas antes de la migración (guardadas en la
    tabla temporal por pre-migration).

    El valor booleano viejo era global, así que lo marcamos True en cada compañía
    raíz del sistema. La escritura usa el ORM —que serializa el jsonb correcto— y
    dispara _propagate_valuation_to_branches, sincronizando el flag a las branches
    de cada grupo.
    """
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'stock_account_mc_ux_shared_migr'
        """
    )
    if not cr.fetchone():
        return

    cr.execute("SELECT categ_id FROM stock_account_mc_ux_shared_migr")
    categ_ids = [row[0] for row in cr.fetchall()]

    if categ_ids:
        env = api.Environment(cr, SUPERUSER_ID, {})
        categs = env["product.category"].browse(categ_ids).exists()
        if categs:
            # Una sola fuente de verdad por grupo: la compañía raíz. La propagación
            # se encarga de sincronizar el flag a las branches.
            root_companies = env["res.company"].search([("parent_id", "=", False)])
            for company in root_companies:
                categs.with_company(company).write({"shared_to_branches": True})

    cr.execute("DROP TABLE IF EXISTS stock_account_mc_ux_shared_migr")
