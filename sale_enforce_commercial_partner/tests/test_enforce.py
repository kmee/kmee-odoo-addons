# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEnforceCommercialPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.company = Partner.create({"name": "Company", "is_company": True})
        cls.invoice_addr = Partner.create(
            {"name": "Invoice", "type": "invoice", "parent_id": cls.company.id}
        )
        cls.delivery_addr = Partner.create(
            {"name": "Delivery", "type": "delivery", "parent_id": cls.company.id}
        )
        cls.person = Partner.create(
            {"name": "Person", "type": "contact", "parent_id": cls.company.id}
        )

    def test_person_uses_commercial_partner_addresses(self):
        order = self.env["sale.order"].create({"partner_id": self.person.id})
        self.assertEqual(order.partner_invoice_id, self.invoice_addr)
        self.assertEqual(order.partner_shipping_id, self.delivery_addr)

    def test_company_keeps_its_own_addresses(self):
        order = self.env["sale.order"].create({"partner_id": self.company.id})
        self.assertEqual(order.partner_invoice_id, self.invoice_addr)
        self.assertEqual(order.partner_shipping_id, self.delivery_addr)
