# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEnforceCommercialPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        Partner = cls.env["res.partner"]
        cls.company_partner = Partner.create({"name": "Corp", "is_company": True})
        # Company level billing and delivery addresses
        cls.corp_invoice = Partner.create(
            {
                "name": "Aaa Corp Billing",
                "type": "invoice",
                "parent_id": cls.company_partner.id,
            }
        )
        cls.corp_delivery = Partner.create(
            {
                "name": "Aaa Corp Warehouse",
                "type": "delivery",
                "parent_id": cls.company_partner.id,
            }
        )
        # Person working for the company, with own (personal) addresses
        cls.person = Partner.create(
            {
                "name": "Zed Person",
                "type": "contact",
                "parent_id": cls.company_partner.id,
            }
        )
        cls.person_invoice = Partner.create(
            {
                "name": "Personal Billing",
                "type": "invoice",
                "parent_id": cls.person.id,
            }
        )
        cls.person_delivery = Partner.create(
            {
                "name": "Personal Delivery",
                "type": "delivery",
                "parent_id": cls.person.id,
            }
        )

    def _order(self, partner):
        return self.env["sale.order"].create({"partner_id": partner.id})

    def test_person_order_uses_company_invoice_address(self):
        """
        Given a person who has a personal billing address and works for a
        company that has its own billing address
        When a quotation is created for the person
        Then the invoice address is the commercial partner billing address
        """
        self.assertEqual(self.person.company_type, "person")
        self.assertEqual(self.person_invoice.company_type, "person")
        order = self._order(self.person)
        self.assertEqual(order.partner_invoice_id, self.corp_invoice)
        self.assertNotEqual(order.partner_invoice_id, self.person_invoice)

    def test_person_order_uses_company_delivery_address(self):
        """
        Given a person with a personal delivery address working for a company
        that has its own delivery address
        When a quotation is created for the person
        Then the shipping address is the commercial partner delivery address
        """
        order = self._order(self.person)
        self.assertEqual(order.partner_shipping_id, self.corp_delivery)
        self.assertNotEqual(order.partner_shipping_id, self.person_delivery)

    def test_changing_partner_recomputes_addresses(self):
        """
        Given a quotation of a company without personal addresses
        When the partner is changed to the person with personal addresses
        Then both addresses follow the commercial partner addresses
        """
        order = self._order(self.company_partner)
        self.assertEqual(order.partner_invoice_id, self.corp_invoice)
        order.partner_id = self.person
        self.assertEqual(order.partner_invoice_id, self.corp_invoice)
        self.assertEqual(order.partner_shipping_id, self.corp_delivery)

    def test_standalone_person_keeps_own_addresses(self):
        """
        Given a person without parent company, with a personal billing address
        When a quotation is created for that person
        Then the commercial partner is the person and the personal address stays
        """
        loner = self.env["res.partner"].create({"name": "Loner"})
        loner_invoice = self.env["res.partner"].create(
            {"name": "Loner Billing", "type": "invoice", "parent_id": loner.id}
        )
        order = self._order(loner)
        self.assertEqual(loner.commercial_partner_id, loner)
        self.assertEqual(order.partner_invoice_id, loner_invoice)

    def test_company_without_children_uses_itself(self):
        """
        Given a company without any child address
        When a quotation is created
        Then invoice and shipping addresses are the company itself
        """
        plain = self.env["res.partner"].create(
            {"name": "Plain Corp", "is_company": True}
        )
        order = self._order(plain)
        self.assertEqual(order.partner_invoice_id, plain)
        self.assertEqual(order.partner_shipping_id, plain)
