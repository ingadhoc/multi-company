from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBranchParentCost(TransactionCase):
    """'Parent's cost, stock on the branches': every branch has its own stock,
    valued at standard cost with the cost the parent sets, and its own valuation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.env["res.company"].create({"name": "Parent Co PC132117"})
        cls.branch = cls.env["res.company"].create({"name": "Branch Co PC132117", "parent_id": cls.parent.id})
        cls.env.user.company_ids = [Command.link(cls.parent.id), Command.link(cls.branch.id)]
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.parent.id, cls.branch.id]))
        # In tests Odoo creates a warehouse for every new company.
        cls.parent_warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.parent.id)])
        cls.branch_warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.branch.id)])
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.categ = (
            cls.env["product.category"]
            .with_company(cls.parent)
            .create(
                {
                    "name": "Parent cost PC132117",
                    "property_cost_method": "average",
                    "property_valuation": "periodic",
                    "shared_to_branches": "parent_cost",
                }
            )
        )
        cls.product = (
            cls.env["product.product"]
            .with_company(cls.parent)
            .create({"name": "Product PC132117", "is_storable": True, "categ_id": cls.categ.id})
        )

    def _receive(self, company, warehouse, quantity, unit_cost):
        move = (
            self.env["stock.move"]
            .with_company(company)
            .create(
                {
                    "product_id": self.product.id,
                    "location_id": self.supplier_location.id,
                    "location_dest_id": warehouse.lot_stock_id.id,
                    "product_uom": self.product.uom_id.id,
                    "product_uom_qty": quantity,
                    "picking_type_id": warehouse.in_type_id.id,
                    "price_unit": unit_cost,
                    "value_manual": unit_cost * quantity,
                }
            )
        )
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()
        return move

    def _costs(self):
        return (
            self.product.with_company(self.parent).standard_price,
            self.product.with_company(self.branch).standard_price,
        )

    def test_branch_costing_is_standard_with_its_own_valuation(self):
        branch_categ = self.categ.with_company(self.branch)
        self.assertEqual(branch_categ.shared_to_branches, "parent_cost")
        self.assertEqual(branch_categ.property_cost_method, "standard")
        self.assertEqual(self.categ.with_company(self.parent).property_cost_method, "average")
        self.assertTrue(branch_categ.is_valuation_shared_from_parent)
        with self.assertRaisesRegex(UserError, "Parent Co PC132117"):
            branch_categ.property_cost_method = "average"
        # The valuation and the accounts stay the branch's own.
        branch_categ.property_valuation = "real_time"
        branch_categ.property_stock_journal = False
        self.categ.with_company(self.parent).property_valuation = "periodic"
        self.assertEqual(branch_categ.property_valuation, "real_time")

        # A change on the parent does not reach the branch's costing method.
        self.categ.with_company(self.parent).property_cost_method = "fifo"
        self.assertEqual(branch_categ.property_cost_method, "standard")

    def test_needs_a_warehouse_on_every_branch(self):
        self.assertTrue(self.categ.with_company(self.parent).can_share_parent_cost)
        self.assertFalse(self.categ.with_company(self.parent).can_share_parent_stock)
        self.branch_warehouse.active = False
        categ = self.env["product.category"].with_company(self.parent).create({"name": "Other PC132117"})
        self.assertFalse(categ.can_share_parent_cost)
        with self.assertRaisesRegex(UserError, "Branch Co PC132117"):
            categ.shared_to_branches = "parent_cost"

    def test_archiving_the_last_branch_warehouse_warns(self):
        warning = self.branch_warehouse.action_archive()
        self.assertEqual(warning["tag"], "display_notification")
        self.assertIn("Branch Co PC132117", warning["params"]["message"])
        self.assertFalse(self.branch_warehouse.active)

        self.categ.with_company(self.parent).shared_to_branches = "none"
        self.branch_warehouse.active = True
        self.assertFalse(self.branch_warehouse.action_archive())

    def test_branch_takes_the_parent_cost(self):
        self.product.with_company(self.parent).standard_price = 100.0
        self.assertEqual(self._costs(), (100.0, 100.0))
        branch_product = self.product.with_company(self.branch)
        self.assertTrue(branch_product.is_cost_shared_from_parent)
        with self.assertRaisesRegex(UserError, "Product PC132117"):
            branch_product.standard_price = 80.0

        # The branch keeps the cost history to value its stock in a closing.
        value = self.env["product.value"].search(
            [("product_id", "=", self.product.id), ("company_id", "=", self.branch.id)], order="id desc", limit=1
        )
        self.assertEqual(value.value, 100.0)

    def test_average_counts_branch_quantities(self):
        """Only the parent's receipts set the cost, over the units of the whole group."""
        self._receive(self.parent, self.parent_warehouse, 10, 10.0)
        self.assertEqual(self._costs(), (10.0, 10.0))

        # A branch purchase adds units at the current cost, whatever it paid.
        self._receive(self.branch, self.branch_warehouse, 10, 50.0)
        self.assertEqual(self._costs(), (10.0, 10.0))

        # (20 units at 10 + 20 at 20) / 40. Counting only the parent's units it would be 16.67.
        self._receive(self.parent, self.parent_warehouse, 20, 20.0)
        self.assertEqual(self._costs(), (15.0, 15.0))

    def test_parent_accounting_value_leaves_out_the_branches(self):
        """Each branch books its own stock: the parent does not add it to its value."""
        account = self.env["account.account"].create(
            {
                "code": "SVPC132",
                "name": "Stock Valuation PC132117",
                "account_type": "asset_current",
                "company_ids": [Command.link(self.parent.id)],
            }
        )
        counterpart = self.env["account.account"].create(
            {
                "code": "CPPC132",
                "name": "Counterpart PC132117",
                "account_type": "expense",
                "company_ids": [Command.link(self.parent.id)],
            }
        )
        journal = self.env["account.journal"].create(
            {"name": "Misc PC132117", "code": "MPC13", "type": "general", "company_id": self.parent.id}
        )
        entry = (
            self.env["account.move"]
            .with_company(self.branch)
            .create(
                {
                    "journal_id": journal.id,
                    "company_id": self.branch.id,
                    "line_ids": [
                        Command.create({"account_id": account.id, "product_id": self.product.id, "debit": 500.0}),
                        Command.create({"account_id": counterpart.id, "credit": 500.0}),
                    ],
                }
            )
        )
        entry.action_post()
        accounts = {self.product: {"valuation": account}}

        self.assertEqual(self.branch.stock_accounting_value(accounts)[account], 500.0)
        self.assertFalse(self.parent.stock_accounting_value(accounts).get(account))
