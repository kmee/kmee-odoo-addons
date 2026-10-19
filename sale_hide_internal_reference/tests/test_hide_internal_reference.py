# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHideInternalReference(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.product = cls.env["product.product"].create(
            {"name": "Widget", "default_code": "WDG-001"}
        )

    def test_default_shows_internal_reference(self):
        """
        Given a product with an internal reference and the flag off (default)
        When the sale description is built
        Then the name carries the internal reference
        """
        self.assertFalse(self.product.hide_internal_reference)
        self.assertEqual(
            self.product.get_product_multiline_description_sale(), "[WDG-001] Widget"
        )

    def test_flag_hides_internal_reference(self):
        """
        Given a product with an internal reference and the flag on
        When the sale description is built
        Then only the product name is used
        """
        self.product.product_tmpl_id.hide_internal_reference = True
        self.assertEqual(
            self.product.get_product_multiline_description_sale(), "Widget"
        )

    def test_description_sale_is_appended(self):
        """
        Given a product with a sales description
        When the description is built with and without the flag
        Then the sales description goes on a new line in both cases
        """
        self.product.description_sale = "Blue edition"
        self.assertEqual(
            self.product.get_product_multiline_description_sale(),
            "[WDG-001] Widget\nBlue edition",
        )
        self.product.product_tmpl_id.hide_internal_reference = True
        self.assertEqual(
            self.product.get_product_multiline_description_sale(),
            "Widget\nBlue edition",
        )

    def test_product_without_reference_is_unaffected(self):
        """
        Given a product without internal reference
        When the flag is toggled
        Then the description is the plain name either way
        """
        plain = self.env["product.product"].create({"name": "Plain"})
        self.assertEqual(plain.get_product_multiline_description_sale(), "Plain")
        plain.product_tmpl_id.hide_internal_reference = True
        self.assertEqual(plain.get_product_multiline_description_sale(), "Plain")

    def test_sale_line_name_uses_the_flag(self):
        """
        Given a sale order line for a product with the flag on
        When the line description is computed
        Then it does not contain the internal reference
        """
        partner = self.env["res.partner"].create({"name": "Customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})

        def line_name():
            line = self.env["sale.order.line"].create(
                {"order_id": order.id, "product_id": self.product.id}
            )
            return line.name

        self.assertIn("[WDG-001]", line_name())
        self.product.product_tmpl_id.hide_internal_reference = True
        self.assertNotIn("WDG-001", line_name())

    def test_flag_is_exposed_in_product_form(self):
        """
        Given the product template form view
        When the view is rendered
        Then the hide_internal_reference field is present
        """
        arch = self.env["product.template"].get_view(
            self.env.ref("product.product_template_form_view").id, "form"
        )["arch"]
        self.assertIn('name="hide_internal_reference"', arch)
