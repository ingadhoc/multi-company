from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBranchSharedScope(TransactionCase):
    """'Shared Stock Valuation to Branches' is only for stock on the parent.

    The branches only invoice: the flag cannot be enabled while a branch has a
    warehouse, a branch cannot get one while the flag is on, and a branch cannot
    change the shared valuation nor the cost of a shared product.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.env["res.company"].create({"name": "Parent Co 132117"})
        cls.branch = cls.env["res.company"].create({"name": "Branch Co 132117", "parent_id": cls.parent.id})
        cls.env.user.company_ids = [Command.link(cls.parent.id), Command.link(cls.branch.id)]
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.parent.id, cls.branch.id]))
        # In tests Odoo creates a warehouse for every new company.
        cls.branch_warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.branch.id)])
        cls.branch_warehouse.active = False
        cls.Category = cls.env["product.category"].with_company(cls.parent)

    def _shared_category(self):
        return self.Category.create(
            {"name": "Shared 132117", "property_cost_method": "standard", "shared_to_branches": True}
        )

    def test_flag_only_without_branch_warehouses(self):
        categ = self.Category.create({"name": "Not shared 132117"})
        self.assertTrue(categ.can_share_to_branches)

        self.branch_warehouse.active = True
        categ.invalidate_recordset(["can_share_to_branches"])
        self.assertFalse(categ.can_share_to_branches)
        with self.assertRaisesRegex(UserError, "Branch Co 132117"):
            categ.shared_to_branches = True
        with self.assertRaises(UserError):
            self._shared_category()

    def test_no_branch_warehouse_while_shared(self):
        self._shared_category()
        with self.assertRaisesRegex(UserError, "cannot have a warehouse"):
            self.branch_warehouse.active = True
        with self.assertRaisesRegex(UserError, "cannot have a warehouse"):
            self.env["stock.warehouse"].create(
                {"name": "Branch WH 132117", "code": "BW132", "company_id": self.branch.id}
            )

        # The parent keeps its own warehouses.
        self.env["stock.warehouse"].create({"name": "Parent WH 132117", "code": "PW132", "company_id": self.parent.id})

    def test_branch_cannot_change_shared_valuation(self):
        categ = self._shared_category()
        branch_categ = categ.with_company(self.branch)
        self.assertEqual(branch_categ.property_cost_method, "standard")
        self.assertTrue(branch_categ.is_valuation_shared_from_parent)
        with self.assertRaisesRegex(UserError, "Parent Co 132117"):
            branch_categ.property_cost_method = "average"

        # Once the parent stops sharing it, the branch configures it on its own.
        categ.shared_to_branches = False
        branch_categ.property_cost_method = "average"
        self.assertEqual(categ.with_company(self.parent).property_cost_method, "standard")

    def test_branch_cannot_change_shared_cost(self):
        categ = self._shared_category()
        product = (
            self.env["product.product"]
            .with_company(self.parent)
            .create({"name": "Product 132117", "is_storable": True, "categ_id": categ.id, "standard_price": 100.0})
        )
        branch_product = product.with_company(self.branch)
        with self.assertRaisesRegex(UserError, "Product 132117"):
            branch_product.standard_price = 80.0
        # Writing the cost it already has is let through, as creating a product does.
        branch_product.standard_price = branch_product.standard_price
        self.env["product.product"].with_company(self.branch).create(
            {"name": "Branch product 132117", "categ_id": categ.id, "standard_price": 0.0}
        )

        product.standard_price = 120.0
        self.assertEqual(branch_product.parent_standard_price, 120.0)
