from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAnalyticDistributionMultiRoot(TransactionCase):
    """Analytic distribution models whose company lives in another company root.

    Covers (helpdesk ticket 133238): given a distribution model with an account prefix in a
    company of another root, when an invoice of that company is created with the active company
    in a different root, then the line takes the distribution of its own model. The account code
    is company dependent and stored on the company root, so reading it from the active root
    returns it empty and no prefix matches.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.active_company = cls.env.company

        other_root = cls.env["res.company"].create({"name": "Other root - (test)"})
        cls.other_company = cls.env["res.company"].create(
            {"name": "Other root child - (test)", "parent_id": other_root.id}
        )

        # the accounts of the other root are created from it, which is where their code is stored
        other_root_accounts = cls.env["account.account"].with_company(cls.other_company)
        cls.other_income_account = other_root_accounts.create(
            {
                "code": "5.0.1.1",
                "name": "Other root income - (test)",
                "account_type": "income",
                "company_ids": [cls.other_company.id],
            }
        )
        other_receivable_account = other_root_accounts.create(
            {
                "code": "1.1.1.1",
                "name": "Other root receivable - (test)",
                "account_type": "asset_receivable",
                "company_ids": [cls.other_company.id],
            }
        )
        cls.other_journal = cls.env["account.journal"].create(
            {
                "name": "Other root sales - (test)",
                "code": "TORS",
                "type": "sale",
                "default_account_id": cls.other_income_account.id,
                "company_id": cls.other_company.id,
            }
        )

        cls.active_income_account = cls.env["account.account"].create(
            {
                "code": "X90001",
                "name": "Active company income - (test)",
                "account_type": "income",
                "company_ids": [cls.active_company.id],
            }
        )
        cls.active_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.active_company.id), ("type", "=", "sale")], limit=1
        )
        if not cls.active_journal:
            cls.active_journal = cls.env["account.journal"].create(
                {
                    "name": "Active company sales - (test)",
                    "code": "TACS",
                    "type": "sale",
                    "default_account_id": cls.active_income_account.id,
                    "company_id": cls.active_company.id,
                }
            )

        plan = cls.env["account.analytic.plan"].create({"name": "Multi root plan - (test)"})
        cls.other_analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Other root analytic - (test)",
                "plan_id": plan.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.active_analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Active company analytic - (test)",
                "plan_id": plan.id,
                "company_id": cls.active_company.id,
            }
        )
        cls.env["account.analytic.distribution.model"].create(
            [
                {
                    "company_id": cls.other_company.id,
                    "account_prefix": "5.0",
                    "analytic_distribution": {str(cls.other_analytic_account.id): 100},
                },
                {
                    "company_id": cls.active_company.id,
                    "account_prefix": "X90",
                    "analytic_distribution": {str(cls.active_analytic_account.id): 100},
                },
            ]
        )

        cls.partner = cls.env["res.partner"].create({"name": "Multi root partner - (test)"})
        cls.partner.with_company(cls.other_company).property_account_receivable_id = other_receivable_account

    def _create_invoice(self, journal, account):
        """Invoice of the journal company, with the active company first: that is how the
        subscription cron bills, with every company allowed and one of them active."""
        return (
            self.env["account.move"]
            .with_context(allowed_company_ids=[self.active_company.id, self.other_company.id])
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner.id,
                    "invoice_date": self.today,
                    "journal_id": journal.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Test product line",
                                "quantity": 1,
                                "price_unit": 100,
                                "account_id": account.id,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )

    def test_analytic_distribution_of_the_line_company(self):
        with self.subTest("una factura de otra raíz toma la analítica de su modelo"):
            invoice = self._create_invoice(self.other_journal, self.other_income_account)
            line = invoice.invoice_line_ids
            self.assertEqual(line.company_id, self.other_company)
            self.assertEqual(line.analytic_distribution, {str(self.other_analytic_account.id): 100})
            self.assertFalse(
                invoice.line_ids.filtered(lambda x: x.display_type == "payment_term").analytic_distribution
            )
            self.assertEqual(invoice.amount_total, 100)

        with self.subTest("una factura de la raíz activa sigue tomando la suya"):
            invoice = self._create_invoice(self.active_journal, self.active_income_account)
            line = invoice.invoice_line_ids
            self.assertEqual(line.company_id, self.active_company)
            self.assertEqual(line.analytic_distribution, {str(self.active_analytic_account.id): 100})
            self.assertEqual(invoice.amount_total, 100)
