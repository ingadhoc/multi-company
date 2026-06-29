from collections import defaultdict

from odoo import models
from odoo.fields import Domain


class ResCompany(models.Model):
    """
    Override de res.company para adaptar el cálculo del valor contable de
    inventario (stock_accounting_value) al modelo de branches con valoración
    compartida.

    Problema que resuelve:
    - En un grupo con padre + branches, los productos con 'shared_to_branches'
      registran sus compras/recepciones en el padre, pero las ventas (COGS) se
      facturan en las branches.
    - BRANCH: esos asientos de COGS sobre la cuenta de valoración no representan
      stock físico de la branch (el stock vive en el padre); inflan su reporte de
      Inventory Valuation con movimientos que se contrarrestan. Hay que excluir
      los productos compartidos del cálculo de la branch.
    - PADRE: si solo cuenta sus propios asientos, ve las compras pero no las
      ventas hechas en las branches, así que su valoración queda alta y el reporte
      le sugiere un ajuste. El padre debe consolidar (consumir) el COGS de las
      branches: sumar los AMLs de todo el grupo para los productos compartidos.

    Nota sobre shared_to_branches: es company_dependent y su fuente de verdad es
    la compañía raíz. Por eso resolvemos las categorías compartidas con
    with_company(root_id) y filtramos por categ_id (campo normal), en vez de
    evaluar el flag company_dependent dentro del dominio (que en contexto de la
    branch puede no estar seteado y no excluiría nada).
    """

    _inherit = "res.company"

    def stock_accounting_value(self, accounts_by_product=None, at_date=None):
        """
        Calcula el valor contable del inventario para la compañía.

        - PADRE (con child_ids): AMLs propios de productos NO compartidos +
          AMLs de TODO el grupo (padre + branches) de productos compartidos, de
          modo que el COGS facturado en las branches consuma su valoración.
        - BRANCH (sin child_ids): solo AMLs propios de productos NO compartidos;
          los compartidos quedan excluidos (su valoración es del padre).

        :param accounts_by_product: dict {product: {valuation: account, ...}}
        :param at_date: fecha de corte (None = saldo actual)
        :return: dict {account.account: balance_sum}
        """
        self.ensure_one()

        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()

        stock_valuation_accounts_ids = {accounts["valuation"].id for accounts in accounts_by_product.values()}

        # Categorías compartidas según la RAÍZ del grupo (fuente de verdad del
        # flag company_dependent). Filtramos por categ_id, no por el flag.
        shared_categ_ids = (
            self.env["product.category"].with_company(self.root_id).search([("shared_to_branches", "=", True)]).ids
        )

        base = Domain(
            [
                ("account_id", "in", list(stock_valuation_accounts_ids)),
                ("parent_state", "=", "posted"),
            ]
        )
        if at_date:
            base &= Domain([("date", "<=", at_date)])

        # --- PADRE ---
        # Comportamiento estándar por ahora. La consolidación del COGS de las
        # branches quedó pendiente de diseño con datos reales: sumar todos los
        # AMLs del grupo sobre-consume (arrastra los asientos de entrega de la
        # branch, no solo el COGS) y deja el contable negativo.
        if self.child_ids:
            domain = base & Domain(
                [
                    ("company_id", "in", self.ids + self.child_ids.ids),
                ]
            )
        elif self.parent_id:
            # --- BRANCH ---
            # Solo asientos propios de productos NO compartidos (los compartidos son
            # valoración del padre; excluirlos limpia el reporte de la branch).
            domain = base & Domain(
                [
                    ("company_id", "=", self.id),
                    ("product_id.categ_id.id", "not in", shared_categ_ids),
                ]
            )
        else:
            return super().stock_accounting_value()
        account_data = defaultdict(float)
        for account, balance in (
            self.env["account.move.line"].sudo()._read_group(domain, ["account_id"], ["balance:sum"])
        ):
            account_data[account] += balance

        return account_data
