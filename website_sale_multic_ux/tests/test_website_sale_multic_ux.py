from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale_multic_ux.controllers.main import WebsiteSale
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestWebsiteSaleMulticUx(WebsiteSaleCommon):
    # Same as website_sale address tests: the checkout runs as the website public user
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website_company = cls.env["res.company"].create({"name": "Website Company Test"})
        cls.env.user.company_ids |= cls.website_company
        cls.website.company_id = cls.website_company
        cls.controller = WebsiteSale()
        cls.address_values = {
            "name": "Checkout Address Test",
            "email": "checkout.address@example.com",
            "street": "Street 123",
            "city": "City",
            "zip": "1200",
            "country_id": cls.country_be.id,
            "phone": "+3233333333",
            "address_type": "delivery",
        }

    def test_anonymous_cart_new_partner_without_company(self):
        public_partner = self.website.user_id.partner_id
        order = self._create_so(partner_id=public_partner.id)
        with self.mock_request(sale_order_id=order.id) as request:
            request.httprequest.method = "POST"
            self.controller.shop_address_submit(partner_id=-1, **self.address_values)
        self.assertNotEqual(order.partner_id, public_partner)
        self.assertFalse(order.partner_id.company_id)

    def test_identified_cart_new_address_keeps_website_company(self):
        partner = self.env["res.partner"].create({"name": "Identified Customer Test"})
        order = self._create_so(partner_id=partner.id)
        with self.mock_request(sale_order_id=order.id) as request:
            request.httprequest.method = "POST"
            self.controller.shop_address_submit(**self.address_values)
        delivery = partner.child_ids.sorted("id")[-1:]
        self.assertTrue(delivery)
        self.assertEqual(delivery.company_id, self.website_company)
