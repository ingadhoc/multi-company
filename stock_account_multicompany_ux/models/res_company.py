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
      registran sus recepciones/compras en el padre, pero las ventas (COGS)
      en las branches.
    - Sin este override, el padre duplicaría el stock (contaría el suyo +
      el de las branches) o las branches lo contarían sin haberlo recibido
      físicamente, inflando los reportes de valoración de inventario.

    Solución:
    - Compañía PADRE: suma sus propios AMLs de productos NO compartidos, más
      todos los AMLs del grupo (padre + branches) de productos compartidos.
      Así consolida el inventario real del grupo en una sola cifra.
    - Compañía BRANCH: suma solo sus propios AMLs de productos NO compartidos.
      Los productos compartidos quedan excluidos para evitar doble conteo con
      el padre.
    """

    _inherit = "res.company"

    def stock_accounting_value(self, accounts_by_product=None, at_date=None):
        """
        Calcula el valor contable del inventario para la compañía.

        Para compañías padre (con child_ids): delega al super() estándar ya que
        el override de dominio solo aplica a branches (compañías sin hijos).
        Para branches (sin child_ids): filtra según shared_to_branches para
        evitar doble conteo con el padre.

        :param accounts_by_product: dict {product: {valuation: account, ...}}
                                    Si no se provee, se calcula internamente.
        :param at_date: fecha de corte para valoración histórica (None = saldo actual)
        :return: dict {account.account: balance_sum}
        """
        if self.child_ids:
            # La compañía padre delega al comportamiento estándar.
            # El super() ya consolida sus hijos si corresponde.
            return super().stock_accounting_value(accounts_by_product=accounts_by_product, at_date=at_date)

        self.ensure_one()

        # Obtener el mapa de cuentas por producto si no fue provisto externamente
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()

        account_data = defaultdict(float)

        # Recolectar todas las cuentas de valoración de stock involucradas
        stock_valuation_accounts_ids = set()
        for dummy, accounts in accounts_by_product.items():
            stock_valuation_accounts_ids.add(accounts["valuation"].id)
        stock_valuation_accounts = self.env["account.account"].browse(stock_valuation_accounts_ids)

        if self.child_ids:
            # --- Compañía PADRE ---
            # Incluir:
            # a) Sus propios AMLs de productos NO compartidos con branches.
            # b) Todos los AMLs del grupo (padre + branches) de productos
            #    compartidos, para consolidar el inventario real en una sola cifra.
            all_branch_company_ids = self._accessible_branches().ids
            domain = Domain(
                [
                    ("account_id", "in", stock_valuation_accounts.ids),
                    ("parent_state", "=", "posted"),
                    "|",
                    # Rama 1: productos no compartidos → solo asientos propios del padre
                    "&",
                    ("product_id.categ_id.shared_to_branches", "!=", True),
                    ("company_id", "=", self.id),
                    # Rama 2: productos compartidos → asientos de todo el grupo
                    "&",
                    ("product_id.categ_id.shared_to_branches", "=", True),
                    ("company_id", "in", all_branch_company_ids),
                ]
            )
        else:
            # --- Compañía BRANCH ---
            # Incluir solo sus propios AMLs de productos NO compartidos.
            # Los productos compartidos son responsabilidad del padre; excluirlos
            # evita inflar la valoración de la branch con stock que físicamente
            # está en el padre (doble conteo en el reporte de Inventory Valuation).
            domain = Domain(
                [
                    ("account_id", "in", stock_valuation_accounts.ids),
                    ("parent_state", "=", "posted"),
                    ("product_id.categ_id.shared_to_branches", "!=", True),
                    ("company_id", "=", self.id),
                ]
            )

        # Aplicar filtro de fecha si se solicita valoración histórica
        if at_date:
            domain = domain & Domain([("date", "<=", at_date)])

        # Agrupar AMLs por cuenta y acumular saldos
        amls_group = self.env["account.move.line"]._read_group(domain, ["account_id"], ["balance:sum"])
        for account, balance in amls_group:
            account_data[account] += balance

        return account_data
