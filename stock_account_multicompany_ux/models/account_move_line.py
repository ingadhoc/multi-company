from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_cogs_value(self):
        """
        Override para calcular el COGS (costo de mercadería vendida) usando el
        costo de la compañía PADRE cuando la línea pertenece a una factura
        emitida por una branch con categoría de producto compartida.

        Contexto:
        - En un esquema multi-compañía con branches, el inventario físico y su
          valoración pueden vivir en la compañía padre.
        - Cuando la branch emite una factura, el costo del producto debe tomarse
          del padre para reflejar fielmente el costo real del inventario vendido.
        - Solo aplica si la categoría del producto tiene 'shared_to_branches' activo.

        Orden de prioridad para determinar el precio unitario:
        1. Precio del asiento original revertido (facturas de rectificación/NC).
        2. stock.move._get_cogs_price_unit() si hay stock moves completados
           (ese método ya tiene su propio override para usar el costo del padre).
        3. Precio estándar del padre (si no hay stock moves, método standard/average).
        4. Última capa SVL del padre como aproximación FIFO.
        5. Precio estándar del padre como fallback final.
        """
        self.ensure_one()

        # Identificar la compañía de la factura y su eventual compañía padre
        branch_company = self.move_id.company_id
        parent_company = branch_company.parent_id

        # Si no hay compañía padre, esta no es una branch → flujo estándar de Odoo
        if not parent_company:
            return super()._get_cogs_value()

        # Solo interceptar si la categoría del producto está marcada como compartida.
        # Para el resto de categorías, la branch tiene su propio inventario y costo.
        if not self.product_id.categ_id.with_company(parent_company.id).shared_to_branches:
            return super()._get_cogs_value()

        # --- Caso 1: Línea de nota de crédito (rectificación) ---
        # Si la factura original ya tiene COGS contabilizado, reutilizar ese precio
        # para garantizar simetría contable y evitar recalcular.
        original_line = self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.product_id == self.product_id
                and l.product_uom_id == self.product_uom_id
                and l.price_unit >= 0
            )
        )
        original_line = original_line and original_line[0]
        if original_line:
            return original_line.price_unit

        # Validaciones básicas: sin producto o cantidad cero no hay COGS que calcular
        if not self.product_id or self.product_uom_id.is_zero(self.quantity):
            return self.price_unit

        cogs_qty = self._get_cogs_qty()

        if moves := self._get_stock_moves().filtered(lambda m: m.state == "done"):
            # --- Caso 2: Hay movimientos de stock completados ---
            # Delegar a stock.move._get_cogs_price_unit(), que está override-ado
            # para retornar el costo de la compañía padre en lugar del de la branch.
            price_unit = moves.with_context(branch_company=branch_company.id)._get_cogs_price_unit(cogs_qty)
        else:
            # --- Caso 3: Sin movimientos de stock ---
            # (ej. servicio con valoración, venta sin picking, ajuste manual)
            # Obtener el costo directamente desde la compañía padre.
            product_parent = self.product_id.with_company(parent_company)

            if product_parent.cost_method in ["standard", "average"]:
                # Standard/Average: usar el precio estándar vigente en el padre
                price_unit = product_parent.standard_price
            else:
                # FIFO: leer la última capa de valoración (SVL) del padre.
                # No se consume ni ajusta ninguna capa; es solo una lectura del costo.
                StockValuationLayer = self.env["stock.valuation.layer"]
                svl = StockValuationLayer.search(
                    [
                        ("product_id", "=", product_parent.id),
                        ("company_id", "=", parent_company.id),
                    ],
                    order="id desc",
                    limit=1,
                )
                if svl:
                    # Usar el costo unitario de la última capa como aproximación FIFO
                    price_unit = svl.unit_cost
                else:
                    # Sin capas previas disponibles: caer al precio estándar del padre
                    price_unit = product_parent.standard_price

        # Descontar el valor de COGS ya contabilizado en asientos anteriores
        # (ej. entregas parciales previamente facturadas) para evitar doble registro.
        # `abs()` es imprescindible: en una nota de crédito `_get_cogs_qty()` devuelve
        # la cantidad negada, por lo que `price_unit * cogs_qty` es negativo. El signo
        # del refund lo aplica `_stock_account_prepare_realtime_out_lines_vals`
        # (sign = -1 if out_refund); si devolviéramos un COGS negativo la doble
        # negación cancelaría esa inversión y el asiento de la NC saldría con la misma
        # dirección que la factura. Se convierte a la UoM del producto igual que Odoo
        # estándar (no usar `self.quantity` crudo: rompe si la línea está en otra UoM).
        line_quantity_uom = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        return abs((price_unit * cogs_qty - self._get_posted_cogs_value()) / line_quantity_uom)
