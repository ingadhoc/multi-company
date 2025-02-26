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
        self.bank_1.write({"partner_id": self.first_company.partner_id.id})
        self.bank_1.company_id = self.first_company.id
        self.env.company = self.first_company

        self.account_receivable = self.env["account.account"].create(
            {"code": "X2022", "name": "Account Receivable Test", "account_type": "asset_receivable", "reconcile": True}
        )

        self.account_payable = self.env["account.account"].create(
            {"code": "X2023", "name": "Account Payable Test", "account_type": "liability_payable", "reconcile": True}
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

        acc.change_company()
        invoice._compute_bank_partner_id()
        invoice._compute_partner_bank_id()
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
            if payable_ctx.property_account_id:  # Ahora sí evalúa con el contexto correcto
                payable_ctx.property_account_id = self.account_payable

        for receivable in self.partner_ri.property_account_receivable_ids:
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
        vendor_bill.action_post()
