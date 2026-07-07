from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestAccountMulticompanyUxUnitTest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.first_company = self.env["res.company"].search([], limit=1)
        self.second_company = self.env["res.company"].search(
            [
                ("id", "!=", self.first_company.id),
                ("account_fiscal_country_id", "=", self.first_company.account_fiscal_country_id.id),
            ],
            limit=1,
        )
        if not self.second_company:
            self.second_company = self.env["res.company"].create({"name": "Test Company 2"})

        self.partner_ri = self.env["res.partner"].search([], limit=1)

        self.first_company_journal = self.env["account.journal"].search(
            [("company_id", "=", self.first_company.id), ("type", "=", "sale")], limit=1
        )
        self.second_company_journal = self.env["account.journal"].search(
            [("company_id", "=", self.second_company.id), ("type", "=", "sale")], limit=1
        )
        self.first_company_purchase_journal = self.env["account.journal"].search(
            [("company_id", "=", self.first_company.id), ("type", "=", "purchase")], limit=1
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
        self.bank_1.allow_out_payment = False
        self.bank_1.write({"partner_id": self.first_company.partner_id.id})
        self.bank_1.company_id = self.first_company.id
        self.bank_1.allow_out_payment = True
        self.env.company = self.first_company

        self.account_receivable = self.env["account.account"].create(
            {
                "code": "X2022",
                "name": "Account Receivable Test",
                "account_type": "asset_receivable",
                "reconcile": True,
                "company_ids": [self.first_company.id],
            }
        )

        self.account_payable = self.env["account.account"].create(
            {
                "code": "X2023",
                "name": "Account Payable Test",
                "account_type": "liability_payable",
                "reconcile": True,
                "company_ids": [self.first_company.id],
            }
        )

    def test_multicompany_sale_order(self):
        """Cambio de compañía de una factura que cuenta con res partner bank seteado para la compañia original"""
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_ri.id,
                "invoice_date": self.today,
                "move_type": "out_invoice",
                "journal_id": self.first_company_journal.id,
                "company_id": self.first_company.id,
                "partner_bank_id": self.bank_1.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        acc = self.env["account.change.company"].create(
            {
                "move_id": invoice.id,
                "company_ids": [self.first_company.id, self.second_company.id],
                "company_id": self.second_company.id,
                "journal_id": self.second_company_journal.id,
            }
        )
        acc.change_company()
        self.assertEqual(
            invoice.partner_bank_id.id,
            False,
            "No se realizo de forma correcta el cambio partner_bank_id al cambiar la compañia",
        )
        acc = self.env["account.change.company"].create(
            {
                "move_id": invoice.id,
                "company_ids": [self.first_company.id, self.second_company.id],
                "company_id": self.first_company.id,
                "journal_id": self.first_company_journal.id,
            }
        )
        self.bank_1.allow_out_payment = False
        self.bank_1.company_id = False
        self.bank_1.allow_out_payment = True
        invoice.write({"partner_bank_id": self.bank_1.id})
        acc.change_company()
        self.assertEqual(
            invoice.partner_bank_id.id,
            self.bank_1.id,
            "No se realizo de forma correcta el cambio partner_bank_id al cambiar la compañia",
        )
        invoice.action_post()

    def test_account_receivable(self):
        """Cambiamos las cuentas por cobrar/pagar y verificamos que impacten correctamente en la factura."""

        # Las cuentas por cobrar y pagar por contacto se encuentran en property_account_receivable_ids y property_account_payable_ids
        # ambas contienen el mismo arreglo con las mismas res.company.property pero solo se puede acceder a ellas mediante el contexto property_field
        # por eso recorremos el arreglo buscando con el contexto respectivo de las account_payable y account_receivable
        for payable in self.partner_ri.property_account_payable_ids:
            payable_ctx = payable.with_context(
                active_model="res.partner", property_field="property_account_payable_id", active_id=self.partner_ri.id
            )
            # Only update if the property belongs to the same company as the account
            if payable_ctx.property_account_id and payable_ctx.company_id == self.first_company:
                payable_ctx.property_account_id = self.account_payable

        for receivable in self.partner_ri.property_account_receivable_ids:
            receivable_ctx = receivable.with_context(
                active_model="res.partner",
                property_field="property_account_receivable_id",
                active_id=self.partner_ri.id,
            )
            # Only update if the property belongs to the same company as the account
            if receivable_ctx.property_account_id and receivable_ctx.company_id == self.first_company:
                receivable_ctx.property_account_id = self.account_receivable

        customer_invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_ri.id,
                "invoice_date": self.today,
                "move_type": "out_invoice",
                "journal_id": self.first_company_journal.id,
                "company_id": self.first_company.id,
                "partner_bank_id": self.bank_1.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        vendor_bill = self.env["account.move"].create(
            {
                "partner_id": self.partner_ri.id,
                "invoice_date": self.today,
                "move_type": "in_invoice",
                "journal_id": self.first_company_purchase_journal.id,
                "company_id": self.first_company.id,
                "partner_bank_id": self.bank_1.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        self.assertTrue(self.account_receivable.id in customer_invoice.line_ids.mapped("account_id.id"))
        self.assertTrue(self.account_payable.id in vendor_bill.line_ids.mapped("account_id.id"))

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
