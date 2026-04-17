from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_realtime_out_lines_vals(self):
        """
        Override para agregar líneas de diferencia de inventario en facturas
        emitidas por compañías branch cuya categoría de producto tiene
        'shared_to_branches' habilitado.

        Cuando una branch usa el costo de la compañía padre, puede existir una
        diferencia entre el precio registrado en la branch y el costo real del
        padre. Este override genera asientos adicionales (líneas de tipo COGS)
        para registrar esa diferencia en la factura.

        Flujo:
        1. Llama al super() para obtener las líneas COGS base.
        2. Solo continúa si la compañía del asiento es una branch (tiene parent_id).
        3. Para cada línea de factura que cumple las condiciones (categoría compartida,
           valoración en tiempo real), busca movimientos de stock 'done' y verifica
           si hubo diferencia de precio registrada en el contexto del move.
        4. Si hay diferencia, construye las líneas adicionales y las agrega a la lista.
        """
        lines_vals_list = super()._stock_account_prepare_realtime_out_lines_vals()

        # Solo proceder si la compañía es una branch (tiene compañía padre).
        # Las compañías padre calculan su propio COGS sin este override.
        if not self.company_id.parent_id:
            return lines_vals_list

        # Iterar únicamente líneas de factura cuyo producto pertenece a una
        # categoría con 'shared_to_branches' activo. El resto usa el flujo
        # estándar de Odoo sin modificaciones.
        for line in self.invoice_line_ids.filtered(lambda x: x.product_id.categ_id.shared_to_branches):
            # Saltar líneas que no generan COGS o productos sin valoración en tiempo real
            if not line._eligible_for_stock_account() or line.product_id.valuation != "real_time":
                continue

            # Obtener los movimientos de stock completados asociados a esta línea de factura
            stock_moves = line._get_stock_moves().filtered(lambda m: m.state == "done")

            for move in stock_moves:
                # La diferencia de inventario se registra en el contexto del move
                # durante el proceso de valoración (ver stock_move._get_cogs_price_unit).
                # Si no hay diferencia registrada, no hay nada que asentar.
                if move._context.get("inventory_price_difference"):
                    price_difference = move._context["inventory_price_difference"]
                    price_diff_account_id = move._context.get("inventory_diff_account")

                    if price_diff_account_id:
                        # Delegar la construcción de los vals al método dedicado en stock.move
                        diff_lines = self.env["stock.move"]._prepare_inventory_difference_lines(
                            self, line, price_difference, self.env["account.account"].browse(price_diff_account_id)
                        )
                        lines_vals_list.extend(diff_lines)

        return lines_vals_list
