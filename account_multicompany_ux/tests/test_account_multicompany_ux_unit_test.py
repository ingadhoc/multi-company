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

    def test_downpayment_taxes_preserved_on_company_change(self):
        """Al cambiar la compañía de una factura de anticipo con 2 alícuotas de IVA,
        las sale.order.line de anticipo deben conservar sus impuestos originales (21% y 10.5%)
        y no colapsar al impuesto único del producto de anticipo (bug: #120730)."""
        # Crear dos impuestos con distinto amount en first_company
        tax_21 = self.env["account.tax"].search(
            [("company_id", "=", self.first_company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 21)],
            limit=1,
        )
        if not tax_21:
            tax_21 = (
                self.env["account.tax"]
                .with_company(self.first_company)
                .create({"name": "IVA 21% Test", "amount": 21, "type_tax_use": "sale"})
            )

        tax_105 = self.env["account.tax"].search(
            [("company_id", "=", self.first_company.id), ("type_tax_use", "=", "sale"), ("amount", "=", 10.5)],
            limit=1,
        )
        if not tax_105:
            tax_105 = (
                self.env["account.tax"]
                .with_company(self.first_company)
                .create({"name": "IVA 10.5% Test", "amount": 10.5, "type_tax_use": "sale"})
            )

        # Impuesto equivalente en second_company (necesario para que el wizard no falle al mapear)
        for tax in [tax_21, tax_105]:
            equiv = self.env["account.tax"].search(
                [
                    ("company_id", "=", self.second_company.id),
                    ("type_tax_use", "=", "sale"),
                    ("amount", "=", tax.amount),
                ],
                limit=1,
            )
            if not equiv:
                self.env["account.tax"].with_company(self.second_company).create(
                    {"name": tax.name + " (C2)", "amount": tax.amount, "type_tax_use": "sale"}
                )

        # Dos productos con distintas alícuotas
        product_a = self.env["product.product"].create(
            {"name": "Producto A (21%)", "taxes_id": [Command.set(tax_21.ids)]}
        )
        product_b = self.env["product.product"].create(
            {"name": "Producto B (10.5%)", "taxes_id": [Command.set(tax_105.ids)]}
        )

        # Orden de venta con ambos productos
        sale_order = (
            self.env["sale.order"]
            .with_company(self.first_company)
            .create(
                {
                    "partner_id": self.partner_ri.id,
                    "company_id": self.first_company.id,
                    "order_line": [
                        Command.create({"product_id": product_a.id, "product_uom_qty": 1, "price_unit": 1000}),
                        Command.create({"product_id": product_b.id, "product_uom_qty": 1, "price_unit": 500}),
                    ],
                }
            )
        )
        sale_order.action_confirm()

        # Facturar anticipo del 50%
        advance_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=sale_order.ids, active_model="sale.order")
            .create({"advance_payment_method": "percentage", "amount": 50})
        )
        advance_wizard.create_invoices()

        # Verificar que se crearon líneas de anticipo con ambas alícuotas
        dp_lines = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        dp_tax_amounts = sorted(dp_lines.mapped("tax_id.amount"))
        self.assertEqual(
            len(dp_lines),
            2,
            "Deben existir 2 líneas de anticipo (una por combinación de impuesto)",
        )
        self.assertIn(21.0, dp_tax_amounts, "Debe haber una línea de anticipo con IVA 21%")
        self.assertIn(10.5, dp_tax_amounts, "Debe haber una línea de anticipo con IVA 10.5%")

        # Obtener la factura de anticipo
        advance_invoice = sale_order.invoice_ids[:1]
        self.assertTrue(advance_invoice, "Debe haberse creado la factura de anticipo")

        # Cambiar compañía de la factura de anticipo
        wizard = self.env["account.change.company"].create(
            {
                "move_id": advance_invoice.id,
                "company_ids": [self.first_company.id, self.second_company.id],
                "company_id": self.second_company.id,
                "journal_id": self.second_company_journal.id,
            }
        )
        wizard.change_company()

        # Verificar que las líneas de anticipo de la VENTA conservan sus impuestos originales
        dp_lines_after = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        dp_tax_amounts_after = sorted(dp_lines_after.mapped("tax_id.amount"))
        self.assertEqual(
            len(dp_lines_after),
            2,
            "Deben seguir existiendo 2 líneas de anticipo tras el cambio de compañía",
        )
        self.assertIn(
            21.0,
            dp_tax_amounts_after,
            "La línea de anticipo con IVA 21% debe conservar su alícuota tras el cambio de compañía",
        )
        self.assertIn(
            10.5,
            dp_tax_amounts_after,
            "La línea de anticipo con IVA 10.5% debe conservar su alícuota (no colapsar al 21%)",
        )
