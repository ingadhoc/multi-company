<<<<<<< e4990f9899b45270526c1cd552b0c43e3c93714d
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
||||||| e83c2c8b0e8be98d691969d9c6ff83db49227309
from odoo import Command, fields
from odoo.tests.common import TransactionCase
=======
from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
>>>>>>> ae725dca450fb5259d92e71f479815771911e730


@tagged("post_install", "-at_install")
class TestAccountMulticompanyUxUnitTest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.first_company = self.env["res.company"].search([], limit=1)
        self.second_company = self.env["res.company"].search([("id", "!=", self.first_company.id)], limit=1)
        if not self.second_company:
            self.second_company = self.env["res.company"].create({"name": "Test Company 2"})

        self.partner_ri = self.env["res.partner"].search([], limit=1)

        self.first_company_journal = self.env["account.journal"].search(
            [("company_id", "=", self.first_company.id), ("type", "=", "sale")], limit=1
        )
        self.second_company_journal = self.env["account.journal"].search(
            [("company_id", "=", self.second_company.id), ("type", "=", "sale")],
            limit=1,
        )
        self.first_company_purchase_journal = self.env["account.journal"].search(
            [("company_id", "=", self.first_company.id), ("type", "=", "purchase")],
            limit=1,
        )

        # Create first company sale journal if not exists
        if not self.first_company_journal:
            a_sale_first = self.env["account.account"].create(
                {
                    "code": "X2024",
                    "name": "Product Sales First - (test)",
                    "account_type": "income",
                    "company_ids": [self.first_company.id],
                }
            )
            self.first_company_journal = self.env["account.journal"].create(
                {
                    "name": "First Customer Invoices - Test",
                    "code": "FINV",
                    "type": "sale",
                    "default_account_id": a_sale_first.id,
                    "company_id": self.first_company.id,
                }
            )

        # Create first company purchase journal if not exists
        if not self.first_company_purchase_journal:
            a_purchase_first = self.env["account.account"].create(
                {
                    "code": "X2025",
                    "name": "Product Purchase First - (test)",
                    "account_type": "expense",
                    "company_ids": [self.first_company.id],
                }
            )
            self.first_company_purchase_journal = self.env["account.journal"].create(
                {
                    "name": "First Vendor Bills - Test",
                    "code": "FBILL",
                    "type": "purchase",
                    "default_account_id": a_purchase_first.id,
                    "company_id": self.first_company.id,
                }
            )

        if not self.second_company_journal:
            a_sale = self.env["account.account"].create(
                {
                    "code": "X2020",
                    "name": "Product Sales - (test)",
                    "account_type": "income",
                    "company_ids": [self.second_company.id],
                }
            )

            self.env["account.account"].create(
                {
                    "code": "X2021",
                    "name": "Product Sales Receivable - (test)",
                    "account_type": "asset_receivable",
                    "company_ids": [self.second_company.id],
                }
            )

            self.second_company_journal = self.env["account.journal"].create(
                {
                    "name": "Second Customer Invoices - Test",
                    "code": "TINV",
                    "type": "sale",
                    "default_account_id": a_sale.id,
                    "company_id": self.second_company.id,
                }
            )

        self.bank_1 = self.env["res.partner.bank"].search([("company_id", "=", False)], limit=1)
        self.bank_1.write({"partner_id": self.first_company.partner_id.id, "allow_out_payment": True})
        self.bank_1.company_id = self.first_company.id

        # Switch to first company context
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.first_company.ids))

        self.account_receivable = self.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_ids", "=", self.first_company.id),
            ],
            limit=1,
        )

        self.account_payable = self.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_ids", "=", self.first_company.id),
            ],
            limit=1,
        )

        # Create accounts if they don't exist
        if not self.account_receivable:
            self.account_receivable = self.env["account.account"].create(
                {
                    "code": "X1100",
                    "name": "Account Receivable Test",
                    "account_type": "asset_receivable",
                    "company_ids": [self.first_company.id],
                }
            )

        if not self.account_payable:
            self.account_payable = self.env["account.account"].create(
                {
                    "code": "X2100",
                    "name": "Account Payable Test",
                    "account_type": "liability_payable",
                    "company_ids": [self.first_company.id],
                }
            )

    def test_company_suffix_uses_short_name(self):
        self._ensure_multi_company_group()

        self.first_company.write({"short_name": "FC"})

        self.assertEqual(self.first_company.get_company_sufix(), " (FC)")
        self.assertEqual(self.first_company.with_context(no_company_sufix=True).get_company_sufix(), "")

    def test_journal_display_name_includes_company_suffix(self):
        self._ensure_multi_company_group()

        self.first_company.write({"short_name": "FC"})
        self.first_company_journal._compute_display_name()

<<<<<<< e4990f9899b45270526c1cd552b0c43e3c93714d
        currency_name = (self.first_company_journal.currency_id or self.first_company.currency_id).name
        expected_display_name = f"{self.first_company_journal.name} ({currency_name})  (FC)"

        self.assertEqual(self.first_company_journal.display_name, expected_display_name)

    def _ensure_multi_company_group(self):
        multi_company_group = self.env.ref("base.group_multi_company")
        if self.env.user.has_group("base.group_multi_company"):
            return

        groups_field = "group_ids" if "group_ids" in self.env.user._fields else "groups_id"
        self.env.user.write({groups_field: [(4, multi_company_group.id)]})
||||||| e83c2c8b0e8be98d691969d9c6ff83db49227309
        self.assertEqual(invoice.company_id, self.second_company)
        self.assertFalse(note.tax_ids)
=======
        self.assertEqual(invoice.company_id, self.second_company)
        self.assertFalse(note.tax_ids)

    def test_payment_term_property_requires_sale_or_invoicing_group(self):
        """The payment term (edit) honors the same groups as the partner form with sale installed."""
        payment_term = self.env.ref("account.account_payment_term_30days")
        base_groups = [self.env.ref("base.group_user").id, self.env.ref("base.group_partner_manager").id]

        def create_user(login, extra_groups):
            return self.env["res.users"].create(
                {
                    "name": login,
                    "login": login,
                    "company_id": self.first_company.id,
                    "company_ids": [Command.set(self.first_company.ids)],
                    "groups_id": [Command.set(base_groups + [self.env.ref(g).id for g in extra_groups])],
                }
            )

        salesman = create_user("mc_salesman", ["sales_team.group_sale_salesman"])
        readonly = create_user("mc_readonly", ["account.group_account_readonly"])
        no_groups = create_user("mc_no_groups", [])

        for property_field in ("property_payment_term_id", "property_supplier_payment_term_id"):
            ctx = {"active_model": "res.partner", "active_id": self.partner_ri.id, "property_field": property_field}
            company_property = self.env["res.company.property"].browse(self.first_company.id)

            company_property.with_user(salesman).with_context(**ctx).property_term_id = payment_term
            self.assertEqual(self.partner_ri.with_company(self.first_company)[property_field], payment_term)

            for user in (readonly, no_groups):
                with self.assertRaises(AccessError):
                    company_property.with_user(user).with_context(**ctx).property_term_id = False
>>>>>>> ae725dca450fb5259d92e71f479815771911e730
