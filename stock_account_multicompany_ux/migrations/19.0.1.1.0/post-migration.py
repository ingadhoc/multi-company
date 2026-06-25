import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Activa shared_to_branches en las categorías automatizadas (real_time)
    presentes en padre y branches (setups A/B migrados sin el flag).

    La lógica vive en product.category.activate_shared_to_branches_for_ab para
    poder reutilizarse también desde la UL 2379.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    activated = env["product.category"].activate_shared_to_branches_for_ab()
    _logger.info(
        "stock_account_multicompany_ux: shared_to_branches activado en %s categorías A/B",
        len(activated),
    )
