from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_cogs_price_unit(self, quantity=0):
        """
        Override: Calcula el precio unitario de COGS usando la valoración de la
        compañía padre cuando el movimiento pertenece a una branch con categoría
        de producto marcada como 'shared_to_branches'.

        Cuando una sucursal factura un producto compartido, el costo debe reflejar
        el inventario real de la compañía padre, no el de la branch (que no posee
        stock físico propio para esos productos).

        Además, si existe diferencia entre el costo del padre y el de la branch,
        la registra mediante _log_inventory_cost_difference para que pueda ser
        usada luego en account_move para generar las líneas de diferencia.

        :param quantity: cantidad en UOM del producto para calcular el costo total
        :return: precio unitario COGS en la moneda de la compañía
        """
        if len(self.product_id) > 1:
            # Recordset con múltiples productos: no se puede calcular un único precio
            return 0

        # Identificar la compañía branch y su padre
        branch_company = self.company_id
        parent_company = branch_company.parent_id

        # Si no hay compañía padre, esta no es una branch → flujo estándar de Odoo
        if not parent_company:
            return super()._get_cogs_price_unit(quantity)

        # Solo interceptar si la categoría tiene 'shared_to_branches' activo.
        # Para otras categorías, la branch gestiona su propio inventario y costo.
        if not self.product_id.categ_id.shared_to_branches:
            return super()._get_cogs_price_unit(quantity)

        # Determinar la cantidad valorada total del recordset
        move_valued_qty = sum(m._get_valued_qty() for m in self)
        cogs_qty = quantity or move_valued_qty
        if not cogs_qty:
            # Sin cantidad, devolver el precio estándar del padre como referencia
            return self.product_id.with_company(parent_company).standard_price

        product_parent = self.product_id.with_company(parent_company)
        product_branch = self.product_id.with_company(branch_company)

        # --- Calcular el precio unitario desde la perspectiva del PADRE ---
        if product_parent.cost_method == "fifo" or (
            product_parent.lot_valuated and product_parent.cost_method == "average"
        ):
            # FIFO o Average con lotes: buscar movimientos equivalentes en el padre
            # para calcular el costo ponderado por cantidad.
            parent_moves = self.env["stock.move"]
            for move in self:
                parent_moves |= move._get_parent_company_moves(parent_company)

            if parent_moves:
                parent_total_qty = sum(m._get_valued_qty() for m in parent_moves)
                if parent_total_qty:
                    # Costo promedio ponderado de los movimientos del padre encontrados
                    parent_price_unit = sum(parent_moves.mapped("value")) / parent_total_qty
                else:
                    parent_price_unit = product_parent.standard_price
            else:
                # Sin movimientos equivalentes en el padre: caer al precio estándar
                parent_price_unit = product_parent.standard_price
        else:
            # Standard o Average sin lotes: precio estándar vigente del padre
            parent_price_unit = product_parent.standard_price

        # --- Calcular el precio unitario desde la perspectiva de la BRANCH ---
        # (necesario para detectar si hay diferencia que registrar)
        if product_branch.cost_method == "fifo" or (
            product_branch.lot_valuated and product_branch.cost_method == "average"
        ):
            # FIFO/Average con lotes en la branch: usar el valor acumulado de los moves
            branch_price_unit = sum(self.mapped("value")) / cogs_qty if cogs_qty else product_branch.standard_price
        else:
            # Standard/Average: precio estándar de la branch
            branch_price_unit = product_branch.standard_price

        # --- Registrar diferencia de costos para auditoría y asientos posteriores ---
        # Si el costo del padre difiere del de la branch, se registra en el contexto
        # del move para que account_move pueda generar las líneas de diferencia.
        if not branch_company.currency_id.is_zero(parent_price_unit - branch_price_unit):
            for move in self:
                move._log_inventory_cost_difference(parent_price_unit, branch_price_unit, move._get_valued_qty())

        # Retornar siempre el precio del PADRE como COGS de la branch
        return parent_price_unit

    def _get_parent_company_moves(self, parent_company):
        """
        Busca los movimientos de stock equivalentes en la compañía padre para
        el producto de este move.

        Se usa para calcular el costo FIFO/Average del padre cuando la branch
        factura un producto compartido. La búsqueda intenta correlacionar el
        move de la branch con el movimiento de recepción del padre usando el
        origen del picking o la orden de venta como referencia cruzada.

        :param parent_company: recordset res.company de la compañía padre
        :return: recordset de stock.move de la compañía padre (puede ser vacío)
        """
        self.ensure_one()

        # Buscar movimientos de entrada completados del mismo producto en el padre
        domain = [
            ("product_id", "=", self.product_id.id),
            ("company_id", "=", parent_company.id),
            ("state", "=", "done"),
            ("is_in", "=", True),  # solo movimientos de entrada (recepciones, ajustes positivos)
        ]

        # Refinar la búsqueda usando referencias cruzadas cuando estén disponibles.
        # El origen del picking (ej. número de PO) o la orden de venta permiten
        # correlacionar movimientos de la branch con los del padre.
        if self.picking_id and self.picking_id.origin:
            domain.append(("picking_id.origin", "=", self.picking_id.origin))
        elif self.sale_line_id and self.sale_line_id.order_id:
            domain.append(("sale_line_id.order_id.name", "=", self.sale_line_id.order_id.name))

        # sudo() necesario porque la branch puede no tener acceso directo a los
        # moves de la compañía padre. Se limita a 10 resultados más recientes.
        parent_moves = self.env["stock.move"].sudo().search(domain, limit=10, order="date desc")

        return parent_moves
