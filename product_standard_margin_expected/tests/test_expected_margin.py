# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExpectedMargin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def _form(self, **values):
        form = Form(self.env["product.template"])
        form.name = "Margin product"
        for key, value in values.items():
            setattr(form, key, value)
        return form

    def test_margin_fills_markup(self):
        """Given a new product, When the expected margin is 20%, Then the
        expected markup becomes 25% (margin / (100 - margin))."""
        form = self._form(expected_margin_percent=20.0)
        self.assertAlmostEqual(form.expected_markup_percent, 25.0)
        product = form.save()
        self.assertAlmostEqual(product.expected_markup_percent, 25.0)
        self.assertAlmostEqual(product.expected_margin_percent, 20.0)

    def test_markup_fills_margin(self):
        """Given a new product, When the expected markup is 100%, Then the
        expected margin becomes 50% (markup / (100 + markup))."""
        form = self._form(expected_markup_percent=100.0)
        self.assertAlmostEqual(form.expected_margin_percent, 50.0)

    def test_round_trip_is_consistent_within_rounding(self):
        """Given a margin typed by the user, When the markup is derived and
        then fed back, Then the margin comes back within the field precision."""
        form = self._form(expected_margin_percent=33.0)
        markup = form.expected_markup_percent
        self.assertAlmostEqual(markup, 49.25, places=2)
        form.expected_markup_percent = markup
        self.assertAlmostEqual(form.expected_margin_percent, 33.0, delta=0.01)

    def test_full_margin_does_not_divide_by_zero(self):
        """Given a 100% margin (infinite markup), Then the markup is left
        untouched and no error is raised."""
        form = self._form(expected_markup_percent=50.0)
        before = form.expected_markup_percent
        form.expected_margin_percent = 100.0
        self.assertEqual(form.expected_margin_percent, 100.0)
        self.assertEqual(form.expected_markup_percent, before)

    def test_negative_margin_gives_negative_markup(self):
        """Given a loss-making expectation of -25% margin, Then the markup is
        -20%."""
        form = self._form(expected_margin_percent=-25.0)
        self.assertAlmostEqual(form.expected_markup_percent, -20.0)

    def test_zero_margin_resets_markup(self):
        """Given margin 20% / markup 25%, When the user sets the margin to 0,
        Then the markup goes to 0 too instead of staying stale."""
        form = self._form(expected_margin_percent=20.0)
        self.assertAlmostEqual(form.expected_markup_percent, 25.0)
        form.expected_margin_percent = 0.0
        self.assertAlmostEqual(form.expected_markup_percent, 0.0)

    def test_zero_markup_resets_margin(self):
        """Given markup 100% / margin 50%, When the user sets the markup to 0,
        Then the margin goes to 0 too."""
        form = self._form(expected_markup_percent=100.0)
        self.assertAlmostEqual(form.expected_margin_percent, 50.0)
        form.expected_markup_percent = 0.0
        self.assertAlmostEqual(form.expected_margin_percent, 0.0)

    def test_markup_of_minus_100_does_not_divide_by_zero(self):
        """Given a markup of -100% (zero price), When it is typed, Then the
        onchange does not raise ZeroDivisionError."""
        form = self._form(expected_markup_percent=50.0)
        form.expected_markup_percent = -100.0
        self.assertAlmostEqual(form.expected_markup_percent, -100.0)

    def test_values_are_rounded_to_two_decimals(self):
        """Given a value with many decimals, When saved, Then it is stored
        with the field precision (5, 2)."""
        product = self.env["product.template"].create(
            {
                "name": "Rounded",
                "expected_margin_percent": 12.3456,
                "expected_markup_percent": 33.3333,
            }
        )
        self.assertEqual(product.expected_margin_percent, 12.35)
        self.assertEqual(product.expected_markup_percent, 33.33)

    def test_create_without_onchange_keeps_fields_independent(self):
        """Given a programmatic create (no UI), Then the two fields are plain
        stored values: setting one does not compute the other."""
        product = self.env["product.template"].create(
            {"name": "Plain", "expected_margin_percent": 20.0}
        )
        self.assertEqual(product.expected_markup_percent, 0.0)

    def test_view_exposes_fields_next_to_standard_markup(self):
        """Given the product form, Then the expected fields are present after
        the computed standard markup field."""
        arch = self.env["product.template"].get_view(view_type="form")["arch"]
        self.assertIn("expected_margin_percent", arch)
        self.assertIn("expected_markup_percent", arch)
        self.assertLess(
            arch.index("standard_markup_rate"), arch.index("expected_margin_percent")
        )
