from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMultiwarehouseGroup(TransactionCase):
    """Auto-activado del permiso "Gestionar varios almacenes" contemplando
    sucursales (branches).

    En modo test, crear una ``res.company`` auto-crea un almacén
    (``stock/models/res_company.py``), por lo que cada compañía creada acá
    arranca con exactamente un almacén.
    """

    def setUp(self):
        super().setUp()
        self.Warehouse = self.env["stock.warehouse"]
        self.group_user = self.env.ref("base.group_user")
        self.group_multi_wh = self.env.ref("stock.group_stock_multi_warehouses")
        self.parent_company = self.env["res.company"].create({"name": "Casa Central Test"})
        self.branch_company = self.env["res.company"].create(
            {"name": "Sucursal Test", "parent_id": self.parent_company.id}
        )

    def test_root_company_is_parent_for_branch(self):
        """La sucursal comparte la compañía raíz con el padre."""
        self.assertEqual(self.parent_company.root_id, self.parent_company)
        self.assertEqual(self.branch_company.root_id, self.parent_company)

    def test_warehouse_count_groups_branch_under_root(self):
        """El almacén de la sucursal se suma al de la compañía raíz.

        Es el núcleo del fix: el core contaría 1 almacén por compañía
        (padre y branch por separado); acá ambos deben acumularse bajo la
        raíz, dando 2.
        """
        parent_whs = self.Warehouse.search([("company_id", "=", self.parent_company.id)])
        branch_whs = self.Warehouse.search([("company_id", "=", self.branch_company.id)])
        self.assertEqual(len(parent_whs), 1)
        self.assertEqual(len(branch_whs), 1)

        cnt_by_root = self.Warehouse._warehouse_count_by_root_company()
        self.assertEqual(
            cnt_by_root[self.parent_company],
            2,
            "El almacén de la sucursal debe sumarse al de la compañía raíz",
        )

    def test_branch_warehouse_activates_multiwarehouse_group(self):
        """Crear una sucursal con almacén auto-activa el permiso.

        Al crearse el almacén de la sucursal se dispara
        ``_check_multiwarehouse_group``; como el grupo raíz pasa a tener 2
        almacenes, el permiso debe quedar implícito en el grupo base.
        """
        self.assertIn(
            self.group_multi_wh,
            self.group_user.implied_ids,
            "El permiso 'Gestionar varios almacenes' debe activarse al haber "
            "una sucursal con almacén bajo la misma compañía raíz",
        )

    def test_archiving_branch_warehouse_recounts_root(self):
        """Al archivar el almacén de la sucursal, la raíz vuelve a contar 1."""
        branch_wh = self.Warehouse.search([("company_id", "=", self.branch_company.id)])
        branch_wh.action_archive()

        cnt_by_root = self.Warehouse._warehouse_count_by_root_company()
        self.assertEqual(
            cnt_by_root[self.parent_company],
            1,
            "Tras archivar el almacén de la sucursal, la raíz debe contar solo "
            "el almacén del padre",
        )
