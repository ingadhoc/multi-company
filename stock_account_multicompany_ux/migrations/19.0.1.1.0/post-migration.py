import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Repobla shared_to_branches (ahora company_dependent / jsonb) a partir de las
    categorías que estaban compartidas antes de la migración (guardadas en la
    tabla temporal por pre-migration).

    El valor booleano viejo era global, así que lo marcamos True en cada compañía
    raíz del sistema cuyas branches no tienen almacenes activos (el flag es para
    stock en la padre y branches que solo facturan); las otras quedan en el log.
    La escritura usa el ORM —que serializa el jsonb correcto— y dispara
    _propagate_valuation_to_branches, sincronizando el flag a las branches de
    cada grupo.
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
                # Only for stock on the parent: with warehouses on the branches the
                # shared valuation does not apply, so it is left off and logged.
                warehouses = company.child_ids and company._get_branch_warehouses()
                if warehouses:
                    _logger.info(
                        "Shared stock valuation not enabled on %s (id %s): branches with active "
                        "warehouses %s. Categories: %s",
                        company.name,
                        company.id,
                        sorted(set(warehouses.company_id.ids)),
                        categs.ids,
                    )
                    continue
                categs.with_company(company).write({"shared_to_branches": "parent_stock"})

    cr.execute("DROP TABLE IF EXISTS stock_account_mc_ux_shared_migr")
