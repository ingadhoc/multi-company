from odoo import Command, fields
from odoo.tests.common import TransactionCase


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
<<<<<<< 16b1a353c6a35b0d752a98586d6001bb878de2c9
        self.bank_1.write({"partner_id": self.first_company.partner_id.id, "allow_out_payment": True})
||||||| 994f6130d463c7fede7f8dc74f42999c3a28251f
        self.bank_1.write({"partner_id": self.first_company.partner_id.id})
=======
        self.bank_1.allow_out_payment = False
        self.bank_1.write({"partner_id": self.first_company.partner_id.id})
>>>>>>> bbeda8abbb8c16c3a16a7fc03ab26b672d7d29a2
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

<<<<<<< 16b1a353c6a35b0d752a98586d6001bb878de2c9
        if not self.account_payable:
            self.account_payable = self.env["account.account"].create(
                {
                    "code": "X2100",
                    "name": "Account Payable Test",
                    "account_type": "liability_payable",
                    "company_ids": [self.first_company.id],
                }
            )
||||||| 994f6130d463c7fede7f8dc74f42999c3a28251f
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
        self.bank_1.company_id = False
        invoice.write({"partner_bank_id": self.bank_1.id})
        acc.change_company()
        self.assertEqual(
            invoice.partner_bank_id.id,
            self.bank_1.id,
            "No se realizo de forma correcta el cambio partner_bank_id al cambiar la compañia",
        )
        invoice.action_post()
=======
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
>>>>>>> bbeda8abbb8c16c3a16a7fc03ab26b672d7d29a2

    def test_account_receivable(self):
        """Cambiamos las cuentas por cobrar/pagar y verificamos que impacten correctamente en la factura."""

        # Las cuentas por cobrar y pagar por contacto se encuentran en property_account_receivable_ids y property_account_payable_ids
        # ambas contienen el mismo arreglo con las mismas res.company.property pero solo se puede acceder a ellas mediante el contexto property_field
        # por eso recorremos el arreglo buscando con el contexto respectivo de las account_payable y account_receivable
        # Filtramos solo las propiedades de la primera compañía
        for payable in self.partner_ri.property_account_payable_ids.filtered(
            lambda x: x.company_id == self.first_company
        ):
            payable_ctx = payable.with_context(
                active_model="res.partner",
                property_field="property_account_payable_id",
                active_id=self.partner_ri.id,
            )
            if payable_ctx.property_account_id:  # Ahora sí evalúa con el contexto correcto
                payable_ctx.property_account_id = self.account_payable

        for receivable in self.partner_ri.property_account_receivable_ids.filtered(
            lambda x: x.company_id == self.first_company
        ):
            receivable_ctx = receivable.with_context(
                active_model="res.partner",
                property_field="property_account_receivable_id",
                active_id=self.partner_ri.id,
            )
            if receivable_ctx.property_account_id:  # Ahora sí evalúa con el contexto correcto
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
        if "l10n_latam_document_number" in self.env["account.move"]._fields:
            vendor_bill.write({"l10n_latam_document_number": "1-1"})
        vendor_bill.action_post()
