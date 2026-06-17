from collections import defaultdict

from odoo import models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _warehouse_count_by_root_company(self):
        """Cantidad de almacenes activos agrupada por compañía raíz.

        El core cuenta agrupando por ``company_id``. Acá sumamos los almacenes
        de las sucursales (branches) al de su compañía padre usando
        ``company_id.root_id`` (la compañía tope de la jerarquía). Para
        compañías sin sucursales ``root_id`` es la propia compañía, por lo que
        el conteo coincide con el estándar.

        :return: dict {res.company (raíz): cantidad de almacenes del grupo}
        """
        cnt_by_company = self.env["stock.warehouse"].sudo()._read_group(
            [("active", "=", True)], ["company_id"], aggregates=["__count"]
        )
        cnt_by_root = defaultdict(int)
        for company, count in cnt_by_company:
            cnt_by_root[company.root_id] += count
        return cnt_by_root

    def _check_multiwarehouse_group(self):
        """Contempla sucursales (branches) al auto-activar el permiso
        "Gestionar varios almacenes" (``stock.group_stock_multi_warehouses``).

        El core agrupa los almacenes activos por ``company_id`` y activa el
        permiso cuando alguna compañía tiene más de un almacén. Con el modelo
        de sucursales (cada branch es una compañía hija con su propio almacén),
        el padre y cada branch quedan con un único almacén, por lo que el
        conteo por compañía nunca supera 1 y el permiso no se activa solo.

        Reescribimos el conteo agrupando por la compañía raíz
        (ver :meth:`_warehouse_count_by_root_company`), de modo que los
        almacenes del grupo (padre + sucursales) se sumen.
        """
        cnt_by_root = self._warehouse_count_by_root_company()
        if not cnt_by_root:
            return

        max_count = max(cnt_by_root.values())

        group_user = self.env.ref("base.group_user")
        group_stock_multi_warehouses = self.env.ref("stock.group_stock_multi_warehouses")
        group_stock_multi_locations = self.env.ref("stock.group_stock_multi_locations")
        if max_count <= 1 and group_stock_multi_warehouses in group_user.implied_ids:
            group_user.write({"implied_ids": [(3, group_stock_multi_warehouses.id)]})
            group_stock_multi_warehouses.write(
                {"user_ids": [(3, user.id) for user in group_user.all_user_ids]}
            )
        if max_count > 1 and group_stock_multi_warehouses not in group_user.implied_ids:
            if group_stock_multi_locations not in group_user.implied_ids:
                self.env["res.config.settings"].create(
                    {"group_stock_multi_locations": True}
                ).execute()
            group_user.write(
                {
                    "implied_ids": [
                        (4, group_stock_multi_warehouses.id),
                        (4, group_stock_multi_locations.id),
                    ]
                }
            )
