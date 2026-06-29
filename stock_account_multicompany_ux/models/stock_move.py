from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_cogs_price_unit(self, quantity=0):
        """
        Override: calcula el precio unitario de COGS usando la valoración de la
        compañía padre cuando el movimiento pertenece a una branch con categoría
        de producto marcada como 'shared_to_branches'.

        Cuando una sucursal factura un producto compartido, el costo debe reflejar
        el inventario real de la compañía padre, no el de la branch (que no posee
        stock físico propio para esos productos).

        La diferencia entre el costo del padre y el de la branch (si existe) NO se
        registra acá: la calcula y asienta account_move._stock_account_prepare_
        realtime_out_lines_vals llamando a _get_inventory_cost_difference, para
        evitar depender de side-effects de contexto entre llamadas.

        :param quantity: cantidad en UOM del producto para calcular el costo total
        :return: precio unitario COGS en la moneda de la compañía
        """
        if len(self.product_id) > 1:
            # Recordset con múltiples productos: no se puede calcular un único precio
            return 0

        # La branch es la compañía de la factura, propagada por _get_cogs_value
        # vía contexto (puede no coincidir con la compañía de los moves).
        branch_context = self.env.context.get("branch_company")
        branch_company = self.env["res.company"].browse(branch_context) if branch_context else False
        if not branch_company:
            return super()._get_cogs_price_unit(quantity)

        parent_company = branch_company.parent_id
        # Solo interceptar si hay padre y la categoría tiene 'shared_to_branches'
        # activo. shared_to_branches es company_dependent: se lee en el contexto del
        # PADRE (fuente de verdad), no de la branch, donde puede no estar seteado.
        if not parent_company or not self.product_id.categ_id.with_company(parent_company).shared_to_branches:
            return super()._get_cogs_price_unit(quantity)

        move_valued_qty = sum(m._get_valued_qty() for m in self)
        cogs_qty = quantity or move_valued_qty
        if not cogs_qty:
            # Sin cantidad, devolver el precio estándar del padre como referencia
            return self.product_id.with_company(parent_company).standard_price

        parent_price_unit, _branch_price_unit = self._get_branch_parent_unit_costs(
            branch_company, parent_company, quantity
        )
        # El COGS de la branch siempre se valúa al costo del PADRE.
        return parent_price_unit

    def _get_branch_parent_unit_costs(self, branch_company, parent_company, quantity=0):
        """
        Calcula el costo unitario del producto de estos moves desde la perspectiva
        del PADRE y de la BRANCH. Usado tanto para el COGS (toma el del padre) como
        para detectar la diferencia padre/branch a asentar.

        Asume un único producto en el recordset (el caller lo garantiza).

        :return: tupla (parent_price_unit, branch_price_unit) en moneda de compañía
        """
        move_valued_qty = sum(m._get_valued_qty() for m in self)
        cogs_qty = quantity or move_valued_qty

        product_parent = self.product_id.with_company(parent_company)
        product_branch = self.product_id.with_company(branch_company)

        # --- Costo unitario desde la perspectiva del PADRE ---
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
                    parent_price_unit = sum(parent_moves.mapped("value")) / parent_total_qty
                else:
                    parent_price_unit = product_parent.standard_price
            else:
                parent_price_unit = product_parent.standard_price
        else:
            # Standard o Average sin lotes: precio estándar vigente del padre
            parent_price_unit = product_parent.standard_price

        # --- Costo unitario desde la perspectiva de la BRANCH ---
        if product_branch.cost_method == "fifo" or (
            product_branch.lot_valuated and product_branch.cost_method == "average"
        ):
            # FIFO/Average con lotes: valor acumulado de los moves de la branch
            branch_price_unit = sum(self.mapped("value")) / cogs_qty if cogs_qty else product_branch.standard_price
        else:
            branch_price_unit = product_branch.standard_price

        return parent_price_unit, branch_price_unit

    def _get_inventory_cost_difference(self, branch_company, parent_company, quantity=0):
        """
        Diferencia total (costo padre - costo branch) * cantidad valorada, en
        moneda de compañía, para los moves de este recordset. Positiva cuando el
        costo del padre es mayor que el de la branch.

        :return: float (0.0 si no hay cantidad o múltiples productos)
        """
        if not self or len(self.product_id) > 1:
            return 0.0

        move_valued_qty = sum(m._get_valued_qty() for m in self)
        cogs_qty = quantity or move_valued_qty
        if not cogs_qty:
            return 0.0

        parent_price_unit, branch_price_unit = self._get_branch_parent_unit_costs(
            branch_company, parent_company, quantity
        )
        return (parent_price_unit - branch_price_unit) * cogs_qty

    def _prepare_inventory_difference_lines(self, move, line, price_difference, diff_account):
        """
        Construye el par balanceado de líneas (display_type='cogs') que asienta la
        diferencia de costo padre/branch:

        - una línea contra la cuenta de diferencia de precio de la categoría;
        - otra contra la cuenta de valoración de stock del producto.

        El par suma cero en amount_currency (asiento balanceado). Con price_difference
        positivo (costo padre > branch): debita la cuenta de diferencia y acredita la
        de valoración.

        Nota contable: este asiento ajusta el residuo que queda en la cuenta de
        valoración/interim por valuar la entrega al costo de la branch y el COGS al
        costo del padre. La cuenta de diferencia es property_price_difference_account_id
        de la categoría. Validar el signo/cuentas contra el asiento esperado.
        """
        accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
        stock_account = accounts["stock_valuation"]
        qty = line.quantity or 1.0
        unit = price_difference / qty

        base_vals = {
            "name": (line.name or "")[:64],
            "move_id": move.id,
            "partner_id": move.commercial_partner_id.id,
            "product_id": line.product_id.id,
            "product_uom_id": line.product_uom_id.id,
            "quantity": line.quantity,
            "analytic_distribution": line.analytic_distribution,
            "display_type": "cogs",
            "tax_ids": [],
            "cogs_origin_id": line.id,
        }
        return [
            {**base_vals, "account_id": diff_account.id, "price_unit": unit, "amount_currency": price_difference},
            {**base_vals, "account_id": stock_account.id, "price_unit": -unit, "amount_currency": -price_difference},
        ]

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
