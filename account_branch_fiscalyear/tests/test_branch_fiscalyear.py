##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBranchFiscalYear(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Test Root 71643",
                "fiscalyear_last_day": 31,
                "fiscalyear_last_month": "7",
            }
        )
        cls.branch = cls.env["res.company"].create(
            {
                "name": "Test Branch 71643",
                "parent_id": cls.company.id,
            }
        )

    def test_01_branch_inherits_fiscalyear_on_create(self):
        """La sucursal nueva nace con el ejercicio de su raíz."""
        self.assertEqual(self.branch.fiscalyear_last_day, 31)
        self.assertEqual(self.branch.fiscalyear_last_month, "7")

    def test_02_branch_can_diverge(self):
        """La sucursal puede tener un cierre distinto al de la raíz."""
        self.branch.write(
            {
                "fiscalyear_last_day": 31,
                "fiscalyear_last_month": "12",
            }
        )
        self.assertEqual(self.branch.fiscalyear_last_month, "12")
        self.assertEqual(self.company.fiscalyear_last_month, "7")

    def test_03_root_write_does_not_propagate(self):
        """Un cambio en la raíz no pisa el ejercicio propio de la sucursal.

        Es la diferencia central con un campo delegado: ahí el `write` de la
        raíz sobreescribe a todas las hijas.
        """
        self.branch.fiscalyear_last_month = "12"
        self.company.fiscalyear_last_month = "4"
        self.assertEqual(self.branch.fiscalyear_last_month, "12")

    def test_04_fiscalyear_dates_follow_the_branch(self):
        """`compute_fiscalyear_dates` de la sucursal usa su propio ejercicio.

        Es el objetivo funcional del módulo: lo que consuma el ejercicio con la
        compañía de la sucursal (amortizaciones, secuencias, libro diario)
        pasa a verlo bien.
        """
        self.branch.write({"fiscalyear_last_day": 31, "fiscalyear_last_month": "12"})
        reference = date(2026, 3, 15)

        root_dates = self.company.compute_fiscalyear_dates(reference)
        branch_dates = self.branch.compute_fiscalyear_dates(reference)

        self.assertEqual(root_dates["date_to"], date(2026, 7, 31))
        self.assertEqual(branch_dates["date_to"], date(2026, 12, 31))

    def test_05_currency_is_still_delegated(self):
        """No tocamos el resto de la delegación: la moneda sigue atada a la raíz."""
        other_currency = self.env["res.currency"].search([("id", "!=", self.company.currency_id.id)], limit=1)
        with self.assertRaises(ValidationError):
            self.branch.currency_id = other_currency
