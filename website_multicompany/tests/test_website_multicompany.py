from odoo.addons.http_routing.tests.common import MockRequest
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteMulticompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Website Company A Test"})
        cls.company_b = cls.env["res.company"].create({"name": "Other Company B Test"})
        cls.website = cls.env["website"].create({"name": "Website Test", "company_id": cls.company_a.id})
        cls.portal_user = cls.env["res.users"].create(
            {
                "name": "Portal User Test",
                "login": "portal_user_multicompany_test",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, (cls.company_a | cls.company_b).ids)],
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )

    def _allowed_companies_on_frontend(self, user):
        with MockRequest(self.env(user=user), website=self.website) as request:

            def update_context(**overrides):
                request.env = request.env(context=dict(request.env.context, **overrides))

            request.update_context = update_context
            request.env["ir.http"]._frontend_pre_dispatch()
            return list(request.env.context["allowed_company_ids"])

    def test_portal_user_sees_all_their_companies(self):
        # The first one becomes env.company on the frontend, so the order matters too
        allowed = self._allowed_companies_on_frontend(self.portal_user)
        self.assertEqual(allowed, self.portal_user.company_ids.ids)

    def test_public_user_keeps_website_company(self):
        allowed = self._allowed_companies_on_frontend(self.website.user_id)
        self.assertEqual(allowed, [self.company_a.id])
