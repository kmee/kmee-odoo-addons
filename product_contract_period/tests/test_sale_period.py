# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import tagged

from odoo.addons.product_contract_period.models.sale_order_line import (
    SaleOrderLine as PeriodSaleOrderLine,
)

from .common import ContractPeriodCase

# The module's own methods are called through its class: other installed modules
# (l10n_br_sale fiscal amounts, product_contract_period_bo onchange) override
# the same methods in the full CI database.


@tagged("post_install", "-at_install")
class TestSalePeriod(ContractPeriodCase):
    def test_product_defaults(self):
        """Given a new product template,
        When nothing is set,
        Then default period qty and count are 1."""
        tmpl = self.env["product.template"].create({"name": "Plan"})
        self.assertEqual(tmpl.default_period_qty, 1.0)
        self.assertEqual(tmpl.default_period_count, 1)

    def test_onchange_product_copies_product_defaults(self):
        """Given a product with 5 licenses over 12 periods by default,
        When the product is chosen on the order line (onchange),
        Then the line period_qty/period_count take the product defaults."""
        self.product.product_tmpl_id.write(
            {"default_period_qty": 5.0, "default_period_count": 12}
        )
        order = self._order([{}])
        line = order.order_line
        line.write({"period_qty": 1.0, "period_count": 1})
        line._onchange_product_id()
        self.assertEqual(line.period_qty, 5.0)
        self.assertEqual(line.period_count, 12)

    def test_line_amount_ignores_period_count(self):
        """Given 2 licenses at 100.00 with 10% discount over 3 periods,
        When the line is computed,
        Then the period amount and subtotal are 2*100*0.9 = 180 (not x3)."""
        order = self._order(
            [
                {
                    "price_unit": 100.0,
                    "discount": 10.0,
                    "period_qty": 2.0,
                    "period_count": 3,
                }
            ]
        )
        line = order.order_line
        self.assertAlmostEqual(line.period_amount, 180.0)
        self.assertAlmostEqual(line.price_subtotal, 180.0)
        # 18.0: the order totals come from the tax base line of each line, so
        # the licenses (not the periods) must be its quantity
        base_line = line._prepare_base_line_for_taxes_computation()
        self.assertEqual(base_line["quantity"], 2.0)
        if "fiscal_quantity" not in line._fields:
            # with l10n_br installed the Brazilian tax engine computes the base
            # line from the fiscal quantity, which this module does not drive
            self.assertAlmostEqual(order.amount_untaxed, 180.0)

    def test_line_tax_computed_on_period_qty(self):
        """Given a 10% tax, 3 licenses at 100.00,
        When the line is computed,
        Then tax is 30 and total 330, driven by period_qty and not product_uom_qty."""
        tax = self.env["account.tax"].create(
            {
                "name": "Tax 10",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        order = self._order(
            [
                {
                    "price_unit": 100.0,
                    "period_qty": 3.0,
                    "product_uom_qty": 9.0,
                    "tax_id": [(6, 0, tax.ids)],
                }
            ]
        )
        line = order.order_line
        PeriodSaleOrderLine._compute_amount(line)
        self.assertAlmostEqual(line.price_subtotal, 300.0)
        self.assertAlmostEqual(line.price_tax, 30.0)
        self.assertAlmostEqual(line.price_total, 330.0)

    def test_line_amount_recomputed_on_period_qty_change(self):
        """Given a line with 1 license,
        When period_qty changes to 4,
        Then subtotal and period_amount follow."""
        order = self._order([{"price_unit": 50.0, "period_qty": 1.0}])
        line = order.order_line
        self.assertAlmostEqual(line.price_subtotal, 50.0)
        line.period_qty = 4.0
        self.assertAlmostEqual(line.price_subtotal, 200.0)
        self.assertAlmostEqual(line.period_amount, 200.0)

    def test_get_date_end_by_rule_type(self):
        """Given 2 periods starting 2026-01-01,
        When the end date is computed for every recurrence,
        Then it is the day before the start of the next period after N periods."""
        order = self._order([{"price_unit": 1.0, "period_count": 2}])
        line = order.order_line
        expected = {
            "daily": date(2026, 1, 2),
            "weekly": date(2026, 1, 14),
            "monthly": date(2026, 2, 28),
            "monthlylastday": date(2026, 2, 28),
            "quarterly": date(2026, 6, 30),
            "semesterly": date(2026, 12, 31),
            "yearly": date(2027, 12, 31),
        }
        for rule, end in expected.items():
            line.recurring_rule_type = rule
            line.date_start = date(2026, 1, 1)
            self.assertEqual(line._get_date_end(), end, rule)

    def test_onchange_period_updates_end_date(self):
        """Given a contract line on the order,
        When period_count changes,
        Then date_end is recomputed from date_start."""
        order = self._order([{"price_unit": 1.0}])
        line = order.order_line
        line.recurring_rule_type = "monthly"
        line.period_count = 6
        PeriodSaleOrderLine._onchange_period(line)
        self.assertEqual(line.date_end, date(2026, 6, 30))

    def test_onchange_period_without_start_date_does_not_crash(self):
        """Given a contract line with no start date,
        When the period changes,
        Then nothing breaks and date_end stays unset."""
        order = self._order([{"price_unit": 1.0}])
        line = order.order_line
        line.write({"date_start": False, "date_end": False})
        PeriodSaleOrderLine._onchange_period(line)
        self.assertFalse(line.date_end)

    def test_onchange_period_ignores_non_contract_product(self):
        """Given a plain product,
        When the period onchange runs,
        Then date_end is untouched."""
        plain = self.env["product.product"].create({"name": "Plain", "type": "service"})
        order = self._order(
            [{"product_id": plain.id, "price_unit": 1.0, "date_end": "2030-01-01"}]
        )
        line = order.order_line
        PeriodSaleOrderLine._onchange_period(line)
        self.assertEqual(line.date_end, date(2030, 1, 1))

    def test_order_period_totals(self):
        """Given two contract lines (monthly 3x and yearly 1x),
        When order totals are computed,
        Then period value, periods, annual and average values are consistent."""
        order = self._order(
            [
                {
                    "price_unit": 100.0,
                    "discount": 10.0,
                    "period_qty": 2.0,
                    "period_count": 3,
                    "recurring_rule_type": "monthly",
                },
                {
                    "price_unit": 1200.0,
                    "period_qty": 1.0,
                    "period_count": 1,
                    "recurring_rule_type": "yearly",
                },
            ]
        )
        # 180 per period (line 1) + 1200 (line 2)
        self.assertAlmostEqual(order.period_contract_value, 1380.0)
        self.assertEqual(order.contract_periods, 4)
        self.assertAlmostEqual(order.contract_annual_value, 1380.0 * 12)
        # total = 180*3 + 1200 = 1740 over 3 + 12 = 15 months
        self.assertAlmostEqual(order.contract_average_value, 1740.0 / 15.0, places=2)
        self.assertIn("License", order.contract_period_details)
        self.assertEqual(len(order.contract_period_details.splitlines()) >= 2, True)

    def test_order_totals_by_rule_type_months(self):
        """Given one line per recurrence with 1 period at 100,
        When the average monthly value is computed,
        Then daily/weekly/quarterly/semesterly use their month length."""
        expected = {
            "daily": 100.0 / (1 / 30.0),
            "weekly": 100.0 / (7 / 30.0),
            "quarterly": 100.0 / 3,
            "semesterly": 100.0 / 6,
        }
        for rule, avg in expected.items():
            order = self._order(
                [
                    {
                        "price_unit": 100.0,
                        "period_count": 1,
                        "recurring_rule_type": rule,
                    }
                ]
            )
            self.assertAlmostEqual(
                order.contract_average_value, avg, places=1, msg=rule
            )

    def test_order_without_contract_lines_has_zero_totals(self):
        """Given an order with only a non contract product,
        When totals are computed,
        Then all period values are zero and details empty."""
        plain = self.env["product.product"].create({"name": "Plain", "type": "service"})
        order = self._order([{"product_id": plain.id, "price_unit": 10.0}])
        self.assertEqual(order.period_contract_value, 0.0)
        self.assertEqual(order.contract_annual_value, 0.0)
        self.assertEqual(order.contract_average_value, 0.0)
        self.assertFalse(order.contract_period_details)
        self.assertFalse(order._get_order_lines_to_report())

    def test_print_values_and_report_lines(self):
        """Given an order with one contract line,
        When print values are requested,
        Then they expose per-line period/annual/total values."""
        order = self._order(
            [
                {
                    "price_unit": 100.0,
                    "discount": 50.0,
                    "period_qty": 2.0,
                    "period_count": 4,
                }
            ]
        )
        data = order.get_period_values_for_print()
        self.assertEqual(len(data["contract_lines"]), 1)
        row = data["contract_lines"][0]
        self.assertAlmostEqual(row["period_value"], 100.0)
        self.assertAlmostEqual(row["annual_value"], 1200.0)
        self.assertAlmostEqual(row["total_value"], 400.0)
        self.assertEqual(data["total_periods"], 4)
        self.assertEqual(order._get_order_lines_to_report(), order.order_line)

    def test_contract_created_from_order_carries_periods(self):
        """Given an order line with 3 licenses over 6 periods,
        When the contract is generated,
        Then the contract line has the same period fields and quantity 3."""
        order = self._order(
            [
                {
                    "price_unit": 10.0,
                    "period_qty": 3.0,
                    "period_count": 6,
                    "recurring_rule_type": "monthly",
                }
            ]
        )
        contract = order.action_create_contract()
        cline = contract.contract_line_ids
        self.assertEqual(len(cline), 1)
        self.assertEqual(cline.period_qty, 3.0)
        self.assertEqual(cline.period_count, 6)
        self.assertEqual(cline.quantity, 3.0)
        self.assertAlmostEqual(cline.period_amount, 30.0)
        self.assertAlmostEqual(cline.total_amount, 180.0)
        self.assertAlmostEqual(contract.total_contract_value, 180.0)
