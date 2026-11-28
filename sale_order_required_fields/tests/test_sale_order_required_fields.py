from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestSaleOrderRequiredFields(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Cliente de teste"})
        cls.product = cls.env["product.product"].create({"name": "Parafuso"})
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [(0, 0, {"product_id": cls.product.id})],
            }
        )

    def test_not_required_by_default(self):
        self.order.payment_mode_id = False
        self.order.payment_term_id = False
        self.order.action_confirm()
        self.assertEqual(self.order.state, "sale")

    def test_required_payment_mode_and_term(self):
        self.company.sale_require_payment_mode = True
        self.company.sale_require_payment_term = True
        self.order.payment_mode_id = False
        self.order.payment_term_id = False
        with self.assertRaises(ValidationError):
            self.order.action_confirm()

    def test_required_line_date(self):
        self.company.sale_require_line_date = True
        with self.assertRaises(ValidationError):
            self.order.action_confirm()
        self.order.order_line.commitment_date = "2030-01-15 12:00:00"
        self.order.action_confirm()
        self.assertEqual(self.order.state, "sale")
