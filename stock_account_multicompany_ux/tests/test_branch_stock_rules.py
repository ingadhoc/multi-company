from odoo import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestBranchStockRules(TransactionCase):
    """The *All Branches* read rules open the tree of every company active in the
    switcher, not only the first one's.

    Two trees: A (root + branch A1) and B (root + branch B1). The user only has access
    to the branches, so the roots' stock is visible only through the permission.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Company = cls.env["res.company"]
        cls.root_a = Company.create({"name": "Root A 130957"})
        cls.branch_a = Company.create({"name": "Branch A1 130957", "parent_id": cls.root_a.id})
        cls.root_b = Company.create({"name": "Root B 130957"})
        cls.branch_b = Company.create({"name": "Branch B1 130957", "parent_id": cls.root_b.id})

        Location = cls.env["stock.location"]
        cls.location_a = Location.create({"name": "Stock A 130957", "usage": "internal", "company_id": cls.root_a.id})
        cls.location_b = Location.create({"name": "Stock B 130957", "usage": "internal", "company_id": cls.root_b.id})

        cls.user = new_test_user(
            cls.env,
            login="branch_stock_130957",
            groups="stock.group_stock_user,stock_account_multicompany_ux.group_stock_all_branches",
            company_id=cls.branch_a.id,
            company_ids=[Command.set([cls.branch_a.id, cls.branch_b.id])],
        )

    def _visible_locations(self, companies):
        locations = self.location_a | self.location_b
        return (
            self.env["stock.location"]
            .with_user(self.user)
            .with_context(allowed_company_ids=companies.ids)
            .search([("id", "in", locations.ids)])
        )

    def test_all_branches_opens_every_active_tree(self):
        companies = self.branch_a | self.branch_b
        self.assertEqual(self._visible_locations(companies), self.location_a | self.location_b)

    def test_all_branches_skips_inactive_tree(self):
        self.assertEqual(self._visible_locations(self.branch_b), self.location_b)

    def test_without_group_sees_only_active_companies(self):
        self.user.group_ids -= self.env.ref("stock_account_multicompany_ux.group_stock_all_branches")
        self.assertFalse(self._visible_locations(self.branch_a | self.branch_b))
