from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBranchSharedCost(TransactionCase):
    """Shared valuation when the stock lives in the branch's own warehouse.

    Standard cost and periodic valuation: the branch moves and stock must be valued
    at the parent's cost, and the branch cannot change that cost or the category.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({"name": "Parent Co 132117"})
        cls.branch_company = cls.env["res.company"].create(
            {"name": "Branch Co 132117", "parent_id": cls.parent_company.id}
        )
        cls.env.user.company_ids = [Command.link(cls.parent_company.id), Command.link(cls.branch_company.id)]
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=[cls.parent_company.id, cls.branch_company.id])
        )
        cls.categ = (
            cls.env["product.category"]
            .with_company(cls.parent_company)
            .create(
                {
                    "name": "Shared Standard 132117",
                    "property_cost_method": "standard",
                    "property_valuation": "periodic",
                    "shared_to_branches": True,
                }
            )
        )
        cls.product = (
            cls.env["product.product"]
            .with_company(cls.parent_company)
            .create({"name": "Product 132117", "is_storable": True, "categ_id": cls.categ.id, "standard_price": 100.0})
        )
        cls.branch_warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.branch_company.id)], limit=1)

    def _branch_receive(self, quantity, company=None):
        company = company or self.branch_company
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        move = (
            self.env["stock.move"]
            .with_company(company)
            .create(
                {
                    "product_id": self.product.id,
                    "product_uom_qty": quantity,
                    "location_id": self.env.ref("stock.stock_location_inter_company").id,
                    "location_dest_id": warehouse.lot_stock_id.id,
                    "company_id": company.id,
                }
            )
        )
        move._action_confirm()
        move.quantity = quantity
        move.picked = True
        move._action_done()
        return move

    def test_branch_moves_and_stock_use_parent_cost(self):
        self.assertTrue(self.branch_warehouse)
        self.assertEqual(self.product.with_company(self.branch_company).standard_price, 100.0)

        move_in = self._branch_receive(10.0)
        self.assertEqual(move_in.value, 1000.0)

        # A cost change on the parent revalues the stock that is in the branch.
        self.product.with_company(self.parent_company).standard_price = 120.0
        branch_product = self.product.with_company(self.branch_company).with_context(
            allowed_company_ids=self.branch_company.ids
        )
        self.assertEqual(branch_product.standard_price, 120.0)
        self.assertEqual(branch_product.total_value, 1200.0)

    def test_parent_quant_value_with_stock_in_both_companies(self):
        """With both companies active, each quant is valued at the shared cost.

        Odoo values a quant as its share of the product's total value over every
        active company: with the branch cost at 0, the parent's value was spread
        over the branch's units too.
        """
        self._branch_receive(200.0, company=self.parent_company)
        self._branch_receive(1000.0)

        quants = (
            self.env["stock.quant"]
            .with_company(self.parent_company)
            .search([("product_id", "=", self.product.id), ("location_id.usage", "=", "internal")])
        )
        self.assertEqual(sum(quants.mapped("quantity")), 1200.0)
        for quant in quants:
            self.assertAlmostEqual(quant.value, quant.quantity * 100.0)

    def test_fifo_branch_takes_parent_cost(self):
        """A FIFO branch keeps FIFO, but values its stock and deliveries at the parent's cost."""
        self.categ.with_company(self.parent_company).property_cost_method = "fifo"
        self.assertEqual(self.categ.with_company(self.branch_company).property_cost_method, "fifo")

        move_in = self._branch_receive(4.0)
        self.assertEqual(move_in.value, 400.0)

        # The parent's FIFO cost moves: the branch's stock and next delivery follow it.
        self.product.with_company(self.parent_company).with_context(
            disable_auto_revaluation=True
        ).standard_price = 150.0
        branch_product = self.product.with_company(self.branch_company).with_context(
            allowed_company_ids=self.branch_company.ids
        )
        self.assertEqual(branch_product.standard_price, 150.0)
        self.assertEqual(branch_product.total_value, 600.0)

        move_out = (
            self.env["stock.move"]
            .with_company(self.branch_company)
            .create(
                {
                    "product_id": self.product.id,
                    "product_uom_qty": 1.0,
                    "location_id": self.branch_warehouse.lot_stock_id.id,
                    "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                    "company_id": self.branch_company.id,
                }
            )
        )
        move_out._action_confirm()
        move_out.quantity = 1.0
        move_out.picked = True
        move_out._action_done()
        self.assertEqual(move_out.value, 150.0)

    def test_secondary_currency_valuation_is_shared(self):
        """With stock_currency_valuation, the currency and the cost in it go to the branch too."""
        if "valuation_currency_id" not in self.categ._fields:
            self.skipTest("stock_currency_valuation is not installed")
        usd = self.env.ref("base.USD")
        usd.active = True
        self.categ.with_company(self.parent_company).valuation_currency_id = usd
        self.assertEqual(self.categ.with_company(self.branch_company).valuation_currency_id, usd)

        self.product.with_company(self.parent_company).standard_price_in_currency = 10.0
        self.assertEqual(self.product.with_company(self.branch_company).standard_price_in_currency, 10.0)

        with self.assertRaises(UserError):
            self.product.with_company(self.branch_company).standard_price_in_currency = 5.0
        with self.assertRaises(UserError):
            self.categ.with_company(self.branch_company).valuation_currency_id = False

    def test_product_entering_shared_category_takes_parent_cost(self):
        categ = self.env["product.category"].with_company(self.parent_company).create({"name": "Other 132117"})
        product = (
            self.env["product.product"]
            .with_company(self.parent_company)
            .create({"name": "Product B 132117", "is_storable": True, "categ_id": categ.id, "standard_price": 70.0})
        )
        self.assertEqual(product.with_company(self.branch_company).standard_price, 0.0)

        product.with_company(self.parent_company).categ_id = self.categ
        self.assertEqual(product.with_company(self.branch_company).standard_price, 70.0)

    def test_branch_cannot_change_shared_valuation(self):
        with self.assertRaises(UserError):
            self.product.with_company(self.branch_company).standard_price = 50.0
        with self.assertRaises(UserError):
            self.categ.with_company(self.branch_company).property_cost_method = "average"
        with self.assertRaises(UserError):
            self.categ.with_company(self.branch_company).property_valuation = "real_time"

    def test_unshared_category_lets_the_branch_configure_itself(self):
        self.categ.with_company(self.parent_company).shared_to_branches = False

        self.categ.with_company(self.branch_company).property_cost_method = "average"
        self.product.with_company(self.branch_company).standard_price = 50.0

        self.assertEqual(self.product.with_company(self.branch_company).standard_price, 50.0)
        self.assertEqual(self.product.with_company(self.parent_company).standard_price, 100.0)
