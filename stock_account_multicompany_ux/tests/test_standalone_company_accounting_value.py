from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStandaloneCompanyAccountingValue(TransactionCase):
    """Valor contable de inventario en una compañía sin padre ni sucursales.

    Es la tercera rama de `stock_accounting_value`, la que delega en el estándar.
    Antes del fix delegaba sin pasar `accounts_by_product` ni `at_date`, así que
    el reporte de valuación y el asiento de cierre comparaban el stock a una
    fecha contra el saldo contable de hoy.

    Los datos se crean a mano (sin plan de cuentas ni demo data) para que el test
    corra igual en una base mínima y en una base OBA completa.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env["res.company"].create({"name": "Standalone Co 75308"})
        cls.env.user.company_ids = [Command.link(cls.company.id)]
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))

        cls.account_stock_valuation = cls._create_account(cls, "SV75308", "Stock Valuation", "asset_current")
        cls.account_other_valuation = cls._create_account(cls, "SO75308", "Other Valuation", "asset_current")
        cls.account_expense = cls._create_account(cls, "EX75308", "Expense", "expense")
        cls.account_income = cls._create_account(cls, "IN75308", "Income", "income")

        cls.journal = (
            cls.env["account.journal"]
            .with_company(cls.company)
            .create(
                {
                    "name": "Stock 75308",
                    "code": "ST753",
                    "type": "general",
                    "company_id": cls.company.id,
                }
            )
        )

        cls.categ = (
            cls.env["product.category"]
            .with_company(cls.company)
            .create(
                {
                    "name": "Real time 75308",
                    "property_cost_method": "standard",
                    "property_valuation": "real_time",
                    "property_account_income_categ_id": cls.account_income.id,
                    "property_account_expense_categ_id": cls.account_expense.id,
                    "property_stock_valuation_account_id": cls.account_stock_valuation.id,
                    "property_stock_journal": cls.journal.id,
                }
            )
        )
        cls.product = (
            cls.env["product.product"]
            .with_company(cls.company)
            .create(
                {
                    "name": "Product 75308",
                    "is_storable": True,
                    "categ_id": cls.categ.id,
                    "standard_price": 100.0,
                }
            )
        )

        # Dos asientos de valoración en períodos distintos: la fecha de corte del
        # test cae en el medio.
        cls._create_valuation_entry(cls, "2026-06-15", 1000.0)
        cls._create_valuation_entry(cls, "2026-08-15", 400.0)

        cls.accounts_by_product = {
            cls.product: {
                "valuation": cls.account_stock_valuation,
                "variation": cls.account_expense,
                "expense": cls.account_expense,
            }
        }

    def _create_account(self, code, name, account_type):
        return (
            self.env["account.account"]
            .with_company(self.company)
            .create(
                {
                    "code": code,
                    "name": name,
                    "account_type": account_type,
                    "company_ids": [Command.link(self.company.id)],
                }
            )
        )

    def _create_valuation_entry(self, date, amount):
        move = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "entry",
                    "company_id": self.company.id,
                    "journal_id": self.journal.id,
                    "date": date,
                    "line_ids": [
                        Command.create({"account_id": self.account_stock_valuation.id, "balance": amount}),
                        Command.create({"account_id": self.account_expense.id, "balance": -amount}),
                    ],
                }
            )
        )
        move.action_post()
        return move

    def test_company_falls_in_the_standalone_branch(self):
        """La compañía del test es la que dispara la rama que delega en el estándar."""
        self.assertFalse(self.company.parent_id)
        self.assertFalse(self.company.child_ids)

    def test_accounting_value_respects_at_date(self):
        """Con fecha de corte solo entran los asientos hasta esa fecha.

        Antes del fix el `super()` se llamaba sin `at_date` y devolvía el saldo de
        hoy, así que el reporte comparaba el stock a la fecha contra la
        contabilidad completa.
        """
        value = self.company.stock_accounting_value(self.accounts_by_product, at_date="2026-06-30")

        self.assertEqual(value[self.account_stock_valuation], 1000.0)

    def test_accounting_value_without_at_date_sums_every_entry(self):
        """Sin fecha de corte el saldo es el total, y difiere del de la fecha."""
        value = self.company.stock_accounting_value(self.accounts_by_product)

        self.assertEqual(value[self.account_stock_valuation], 1400.0)

    def test_accounting_value_respects_accounts_by_product(self):
        """Las cuentas las fija el llamador, no el recálculo del estándar.

        Antes del fix el `super()` se llamaba sin `accounts_by_product` y lo
        recalculaba para todos los productos valuables, trayendo cuentas fuera
        del alcance de la llamada.
        """
        accounts_by_product = {
            self.product: {
                "valuation": self.account_other_valuation,
                "variation": self.account_expense,
                "expense": self.account_expense,
            }
        }

        value = self.company.stock_accounting_value(accounts_by_product)

        self.assertNotIn(self.account_stock_valuation, value)
