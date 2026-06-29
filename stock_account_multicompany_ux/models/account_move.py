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
        1. Llama al super() para obtener las líneas COGS base (ya valuadas al costo
           del padre, vía el override de account_move_line._get_cogs_value).
        2. Solo continúa si la compañía del asiento es una branch (tiene parent_id).
        3. Para cada línea de factura que cumple las condiciones (categoría compartida,
           valoración en tiempo real) con movimientos de stock 'done', calcula la
           diferencia de costo padre/branch directamente sobre los moves.
        4. Si la diferencia no es cero, construye el par de líneas balanceadas y las
           agrega a la lista. Si el costo está unificado (objetivo de shared_to_branches),
           la diferencia es 0 y no se agrega nada.
        """
        lines_vals_list = super()._stock_account_prepare_realtime_out_lines_vals()

        # Solo proceder si la compañía es una branch (tiene compañía padre).
        # Las compañías padre calculan su propio COGS sin este override.
        branch_company = self.company_id
        parent_company = branch_company.parent_id
        if not parent_company:
            return lines_vals_list

        # Iterar únicamente líneas de factura cuyo producto pertenece a una
        # categoría con 'shared_to_branches' activo. El flag es company_dependent:
        # se lee en el contexto del PADRE (fuente de verdad), no de la branch.
        # El resto usa el flujo estándar de Odoo sin modificaciones.
        for line in self.invoice_line_ids.filtered(
            lambda x: x.product_id.categ_id.with_company(parent_company).shared_to_branches
        ):
            # Saltar líneas que no generan COGS o productos sin valoración en tiempo real
            if not line._eligible_for_stock_account() or line.product_id.valuation != "real_time":
                continue

            # Movimientos de stock completados asociados a esta línea de factura
            stock_moves = line._get_stock_moves().filtered(lambda m: m.state == "done")
            if not stock_moves:
                continue

            # Cuenta de diferencia de precio de la categoría (company_dependent → padre)
            diff_account = line.product_id.categ_id.with_company(parent_company).property_price_difference_account_id
            if not diff_account:
                continue

            # Diferencia (costo padre - costo branch) * cantidad valorada de los moves.
            sign = -1 if self.move_type == "out_refund" else 1
            price_difference = sign * stock_moves._get_inventory_cost_difference(branch_company, parent_company)
            if self.currency_id.is_zero(price_difference):
                continue

            lines_vals_list += self.env["stock.move"]._prepare_inventory_difference_lines(
                self, line, price_difference, diff_account
            )

        return lines_vals_list
