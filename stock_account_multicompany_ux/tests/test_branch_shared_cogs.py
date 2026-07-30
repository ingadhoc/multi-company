from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBranchSharedCogs(TransactionCase):
    """COGS de una branch para categorías con valoración compartida.

    Los datos se crean a mano (sin plan de cuentas ni demo data) para que el test
    corra igual en una base mínima y en una base OBA completa.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.parent_company = cls.env["res.company"].create({"name": "Parent Co 71584"})
        cls.branch_company = cls.env["res.company"].create(
            {"name": "Branch Co 71584", "parent_id": cls.parent_company.id}
        )
        cls.env.user.company_ids = [Command.link(cls.parent_company.id), Command.link(cls.branch_company.id)]
        # La branch va primera: la propagación de shared_to_branches solo alcanza
        # a las branches accesibles en el contexto.
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=[cls.branch_company.id, cls.parent_company.id])
        )

        cls.account_receivable = cls._create_account(cls, "AR71584", "Receivable", "asset_receivable")
        cls.account_income = cls._create_account(cls, "IN71584", "Income", "income")
        cls.account_expense = cls._create_account(cls, "EX71584", "Expense", "expense")
        cls.account_stock_valuation = cls._create_account(cls, "SV71584", "Stock Valuation", "asset_current")

        cls.journal_sale = (
            cls.env["account.journal"]
            .with_company(cls.parent_company)
            .create(
                {
                    "name": "Sales 71584",
                    "code": "SA716",
                    "type": "sale",
                    "company_id": cls.parent_company.id,
                    "default_account_id": cls.account_income.id,
                }
            )
        )
        cls.journal_stock = (
            cls.env["account.journal"]
            .with_company(cls.parent_company)
            .create(
                {
                    "name": "Stock 71584",
                    "code": "ST716",
                    "type": "general",
                    "company_id": cls.parent_company.id,
                }
            )
        )

        cls.categ = (
            cls.env["product.category"]
            .with_company(cls.parent_company)
            .create(
                {
                    "name": "Shared FIFO 71584",
                    "property_cost_method": "fifo",
                    "property_valuation": "real_time",
                    "shared_to_branches": True,
                    "property_account_income_categ_id": cls.account_income.id,
                    "property_account_expense_categ_id": cls.account_expense.id,
                    "property_stock_valuation_account_id": cls.account_stock_valuation.id,
                    "property_stock_journal": cls.journal_stock.id,
                }
            )
        )

        cls.product = (
            cls.env["product.product"]
            .with_company(cls.parent_company)
            .create(
                {
                    "name": "Product 71584",
                    "is_storable": True,
                    "categ_id": cls.categ.id,
                    "standard_price": 100.0,
                }
            )
        )

        # Entrada valorizada en el padre: 10 unidades a 100 => el stack FIFO del
        # padre vale 100 por unidad.
        warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.parent_company.id)], limit=1)
        move = (
            cls.env["stock.move"]
            .with_company(cls.parent_company)
            .create(
                {
                    "product_id": cls.product.id,
                    "product_uom_qty": 10.0,
                    "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                    "location_dest_id": warehouse.lot_stock_id.id,
                    "company_id": cls.parent_company.id,
                }
            )
        )
        move._action_confirm()
        move.quantity = 10.0
        move.picked = True
        move._action_done()
        cls.parent_in_move = move

        # Precio estándar distinto del costo real de la entrada: si el COGS sale 500
        # es porque cayó al standard price en vez de valuar contra el FIFO del padre.
        cls.product.with_company(cls.parent_company).standard_price = 500.0

        cls.partner = cls.env["res.partner"].create({"name": "Customer 71584"})
        for company in (cls.parent_company, cls.branch_company):
            cls.partner.with_company(company).property_account_receivable_id = cls.account_receivable

    def _create_account(self, code, name, account_type):
        return (
            self.env["account.account"]
            .with_company(self.parent_company)
            .create(
                {
                    "code": code,
                    "name": name,
                    "account_type": account_type,
                    "company_ids": [Command.link(self.parent_company.id)],
                }
            )
        )

    def _create_branch_invoice(self, quantity=3.0):
        """Factura de la branch sin movimientos de stock asociados."""
        return (
            self.env["account.move"]
            .with_company(self.branch_company)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": self.branch_company.id,
                    "partner_id": self.partner.id,
                    "journal_id": self.journal_sale.id,
                    "invoice_date": "2026-01-15",
                    "invoice_date_due": "2026-01-15",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "quantity": quantity,
                                "price_unit": 150.0,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )

    def test_setup_is_the_fifo_without_moves_scenario(self):
        """El escenario es el que dispara la rama FIFO sin movimientos de stock."""
        invoice = self._create_branch_invoice()
        line = invoice.invoice_line_ids

        self.assertEqual(invoice.company_id, self.branch_company)
        self.assertTrue(invoice.company_id.parent_id)
        self.assertTrue(self.categ.with_company(self.parent_company).shared_to_branches)
        self.assertEqual(self.product.with_company(self.parent_company).cost_method, "fifo")
        self.assertEqual(self.product.with_company(self.branch_company).valuation, "real_time")
        self.assertFalse(line._get_stock_moves().filtered(lambda m: m.state == "done"))

    def test_cogs_value_uses_parent_fifo_stack(self):
        """Sin stock moves y con FIFO, el COGS se valúa contra el FIFO del padre.

        Antes del fix este camino leía `stock.valuation.layer`, modelo eliminado en
        Odoo 19, y levantaba KeyError.
        """
        invoice = self._create_branch_invoice()

        self.assertEqual(invoice.invoice_line_ids._get_cogs_value(), 100.0)

    def test_post_generates_balanced_cogs_at_parent_cost(self):
        """Confirmar la factura genera el par de COGS al costo del padre."""
        invoice = self._create_branch_invoice()

        invoice.action_post()

        cogs_lines = invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertEqual(len(cogs_lines), 2)
        self.assertEqual(sum(cogs_lines.mapped("debit")), 300.0)
        self.assertEqual(sum(cogs_lines.mapped("credit")), 300.0)
        self.assertEqual(
            cogs_lines.filtered(lambda line: line.debit).account_id,
            self.account_expense,
        )
        self.assertEqual(
            cogs_lines.filtered(lambda line: line.credit).account_id,
            self.account_stock_valuation,
        )

    def test_cogs_value_falls_back_to_standard_price_without_parent_stock(self):
        """Sin entradas en el padre, FIFO extrapola con el precio estándar del padre."""
        product = (
            self.env["product.product"]
            .with_company(self.parent_company)
            .create(
                {
                    "name": "Product 71584 sin stock",
                    "is_storable": True,
                    "categ_id": self.categ.id,
                    "standard_price": 250.0,
                }
            )
        )
        invoice = self._create_branch_invoice()
        invoice.invoice_line_ids.product_id = product

        self.assertEqual(invoice.invoice_line_ids._get_cogs_value(), 250.0)

    def test_cogs_value_untouched_when_category_not_shared(self):
        """Categoría sin shared_to_branches: el override no interviene."""
        categ = (
            self.env["product.category"]
            .with_company(self.parent_company)
            .create(
                {
                    "name": "Not shared 71584",
                    "property_cost_method": "standard",
                    "property_valuation": "real_time",
                    "property_account_income_categ_id": self.account_income.id,
                    "property_account_expense_categ_id": self.account_expense.id,
                    "property_stock_valuation_account_id": self.account_stock_valuation.id,
                    "property_stock_journal": self.journal_stock.id,
                }
            )
        )
        product = (
            self.env["product.product"]
            .with_company(self.parent_company)
            .create(
                {
                    "name": "Product 71584 no compartido",
                    "is_storable": True,
                    "categ_id": categ.id,
                    "standard_price": 900.0,
                }
            )
        )
        # Cada compañía con su propio costo: sin categoría compartida el COGS de la
        # branch se valúa con el costo de la branch, no con el del padre.
        product.with_company(self.branch_company).standard_price = 70.0
        invoice = self._create_branch_invoice()
        invoice.invoice_line_ids.product_id = product

        self.assertFalse(categ.with_company(self.parent_company).shared_to_branches)
        self.assertEqual(invoice.invoice_line_ids._get_cogs_value(), 70.0)
