from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountChangeCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({"name": "Casa Matriz Test"})
        cls.branch_a = cls.env["res.company"].create(
            {"name": "Sucursal Centro Test", "parent_id": cls.parent_company.id}
        )
        cls.branch_b = cls.env["res.company"].create(
            {"name": "Sucursal Norte Test", "parent_id": cls.parent_company.id}
        )
        cls.branch_a_child = cls.env["res.company"].create({"name": "Centro AUX Test", "parent_id": cls.branch_a.id})

        cls.env.user.write(
            {
                "company_ids": [
                    (4, c.id) for c in (cls.parent_company + cls.branch_a + cls.branch_b + cls.branch_a_child)
                ]
            }
        )

        income_account = cls.env["account.account"].create(
            {
                "code": "X9100",
                "name": "Branch A Income - (test)",
                "account_type": "income",
                "company_ids": [cls.branch_a.id],
            }
        )
        branch_a_journal = cls.env["account.journal"].create(
            {
                "name": "Branch A Invoices - Test",
                "code": "BAINV",
                "type": "sale",
                "default_account_id": income_account.id,
                "company_id": cls.branch_a.id,
            }
        )
        cls.move = (
            cls.env["account.move"]
            .with_company(cls.branch_a)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": cls.branch_a.id,
                    "journal_id": branch_a_journal.id,
                }
            )
        )

        grandchild_income_account = cls.env["account.account"].create(
            {
                "code": "X9200",
                "name": "Centro AUX Income - (test)",
                "account_type": "income",
                "company_ids": [cls.branch_a_child.id],
            }
        )
        grandchild_journal = cls.env["account.journal"].create(
            {
                "name": "Centro AUX Invoices - Test",
                "code": "GCINV",
                "type": "sale",
                "default_account_id": grandchild_income_account.id,
                "company_id": cls.branch_a_child.id,
            }
        )
        cls.grandchild_move = (
            cls.env["account.move"]
            .with_company(cls.branch_a_child)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": cls.branch_a_child.id,
                    "journal_id": grandchild_journal.id,
                }
            )
        )

    def _wizard_company_ids(self, allowed_companies, move=None):
        wizard = (
            self.env["account.change.company"]
            .with_context(active_id=(move or self.move).id, allowed_company_ids=allowed_companies.ids)
            .new({})
        )
        return wizard.company_ids._origin

    def test_sibling_company_is_listed(self):
        """Parado en una sucursal, el wizard debe ofrecer tanto la casa matriz
        como las sucursales hermanas, no solo la matriz (tarea #70688)."""
        company_ids = self._wizard_company_ids(self.parent_company + self.branch_a + self.branch_b)
        self.assertIn(self.branch_b, company_ids, "La sucursal hermana debería estar disponible")
        self.assertIn(self.parent_company, company_ids, "La casa matriz debería estar disponible")
        self.assertNotIn(self.branch_a, company_ids, "La propia compañía actual no debe listarse")

    def test_only_allowed_companies_are_listed(self):
        """El listado debe respetar allowed_company_ids del usuario, aunque
        haya más hermanas en la jerarquía (tarea #70688)."""
        company_ids = self._wizard_company_ids(self.parent_company + self.branch_a)
        self.assertNotIn(self.branch_b, company_ids, "No debería listar compañías fuera de allowed_company_ids")

    def test_no_crash_without_move_context(self):
        """Sin active_id en el contexto, move_id (y por lo tanto company_id)
        queda vacío; el cómputo no debe romper con ensure_one()."""
        wizard = self.env["account.change.company"].new({})
        self.assertFalse(wizard.company_ids)

    def test_grandchild_reaches_whole_tree(self):
        """Parado en un nieto (3er nivel: Casa Matriz -> Sucursal Centro -> Centro AUX),
        el wizard debe ofrecer toda la jerarquía accesible: la raíz, el padre directo
        y las hermanas del padre — no solo el padre directo (ejemplo de Nico Col)."""
        allowed = self.parent_company + self.branch_a + self.branch_b + self.branch_a_child
        company_ids = self._wizard_company_ids(allowed, move=self.grandchild_move)
        self.assertIn(self.parent_company, company_ids, "La raíz (abuela) debería estar disponible")
        self.assertIn(self.branch_a, company_ids, "El padre directo debería estar disponible")
        self.assertIn(self.branch_b, company_ids, "La hermana del padre (tía) debería estar disponible")
        self.assertNotIn(self.branch_a_child, company_ids, "La propia compañía actual no debe listarse")
