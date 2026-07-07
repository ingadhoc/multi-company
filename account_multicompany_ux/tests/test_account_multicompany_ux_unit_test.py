from odoo import fields
from odoo.tests.common import TransactionCase, tagged


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

<<<<<<< 0ee9f15bc252ab29f2ef0e265a27d8adc00a24cb
        self.assertEqual(self.first_company.get_company_sufix(), " (FC)")
        self.assertEqual(self.first_company.with_context(no_company_sufix=True).get_company_sufix(), "")

    def test_journal_display_name_includes_company_suffix(self):
        self._ensure_multi_company_group()

        self.first_company.write({"short_name": "FC"})
        self.first_company_journal._compute_display_name()

        currency_name = (self.first_company_journal.currency_id or self.first_company.currency_id).name
        expected_display_name = f"{self.first_company_journal.name} ({currency_name})  (FC)"

        self.assertEqual(self.first_company_journal.display_name, expected_display_name)

    def _ensure_multi_company_group(self):
        multi_company_group = self.env.ref("base.group_multi_company")
        if self.env.user.has_group("base.group_multi_company"):
            return

        groups_field = "group_ids" if "group_ids" in self.env.user._fields else "groups_id"
        self.env.user.write({groups_field: [(4, multi_company_group.id)]})
||||||| b861a87a71667da9a388f71ec133298aff66a7be
        customer_invoice.action_post()
        vendor_bill.action_post()
=======
        customer_invoice.action_post()
        vendor_bill.action_post()

    def test_change_company_keeps_ar_perception_move_line(self):
        """Regresión ticket 122289: al cambiar de compañía una factura con percepción AR,
        el apunte contable de la percepción debe seguir existiendo.

        El recompute de percepciones corre bajo ``skip_invoice_sync``; ``_sync_tax_lines``
        solo genera la move line de un impuesto si el ``tax_ids`` de la base line cambia
        DENTRO del bloque ``_sync_dynamic_lines`` final. Si el recompute corriera antes del
        bloque, el snapshot ya vería la percepción puesta y no se crearía el apunte.

        Solo aplica con la localización AR instalada (``l10n_ar_tax``), que no es dependencia
        de este módulo; en su ausencia el test se saltea.
        """
        AFP = self.env["account.fiscal.position"]
        if "l10n_ar_tax_ids" not in AFP._fields:
            self.skipTest("l10n_ar_tax no instalado: las percepciones AR no aplican")

        def _ar_company(exclude=None):
            """Devuelve (company, fiscal_position, sale_journal) para una compañía AR con
            posición fiscal de percepción, o (None, None, None)."""
            companies = self.env["res.company"].search([("account_fiscal_country_id.code", "=", "AR")])
            for company in companies - (exclude or self.env["res.company"]):
                fp = AFP.search(
                    [("company_id", "=", company.id), ("l10n_ar_tax_ids.tax_type", "=", "perception")],
                    limit=1,
                )
                journal = self.env["account.journal"].search(
                    [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
                )
                if fp and journal:
                    return company, fp, journal
            return None, None, None

        company_a, fp_a, journal_a = _ar_company()
        if not company_a:
            self.skipTest("No hay compañía AR con posición fiscal de percepción")
        company_b, _fp_b, journal_b = _ar_company(exclude=company_a)
        if not company_b:
            self.skipTest("No hay una segunda compañía AR con posición fiscal de percepción")

        # Grupos de impuesto de todas las percepciones AR configuradas (para identificar
        # las tax lines de percepción sin depender de la identidad de grupo por compañía).
        perception_groups = (
            AFP.search([("l10n_ar_tax_ids.tax_type", "=", "perception")])
            .mapped("l10n_ar_tax_ids")
            .filtered(lambda x: x.tax_type == "perception")
            .mapped("default_tax_id.tax_group_id")
        )

        partner = self.env["res.partner"].search([("parent_id", "=", False)], limit=1)
        product = self.env.ref("product.product_product_16")

        invoice = (
            self.env["account.move"]
            .with_company(company_a)
            .create(
                {
                    "partner_id": partner.id,
                    "invoice_date": self.today,
                    "move_type": "out_invoice",
                    "journal_id": journal_a.id,
                    "company_id": company_a.id,
                    "fiscal_position_id": fp_a.id,
                    "invoice_line_ids": [
                        Command.create({"product_id": product.id, "quantity": 1, "price_unit": 100}),
                    ],
                }
            )
        )
        # Forzamos el cómputo de percepciones como lo hace la UI (onchange).
        invoice._l10n_ar_recompute_fiscal_position_taxes()

        def _perception_tax_lines(move):
            return move.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.tax_group_id in perception_groups)

        # Baseline: la factura de origen debe tener el apunte de percepción; si la posición
        # fiscal no lo aplicó a este partner/producto, el caso no es reproducible.
        if not _perception_tax_lines(invoice):
            self.skipTest("La posición fiscal no aplicó percepción a la factura de prueba")

        self.env["account.change.company"].create(
            {
                "move_id": invoice.id,
                "company_ids": [company_a.id, company_b.id],
                "company_id": company_b.id,
                "journal_id": journal_b.id,
            }
        ).change_company()

        self.assertTrue(
            _perception_tax_lines(invoice),
            "No se generó el apunte contable de la percepción tras el cambio de compañía (ticket 122289)",
        )
>>>>>>> 6844a869c49a1d167d07117c47ca817bc7477348
