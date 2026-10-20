# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import tagged

from .common import ContractPeriodCase


@tagged("post_install", "-at_install")
class TestContractPeriod(ContractPeriodCase):
    def test_line_amounts_with_discount(self):
        """Given 2 licenses at 50 with 20% discount over 6 periods,
        When the amounts are computed,
        Then period = 80 and total = 480."""
        contract = self._contract(
            [
                {
                    "price_unit": 50.0,
                    "discount": 20.0,
                    "period_qty": 2.0,
                    "period_count": 6,
                }
            ]
        )
        line = contract.contract_line_ids
        self.assertAlmostEqual(line.period_amount, 80.0)
        self.assertAlmostEqual(line.total_amount, 480.0)
        self.assertAlmostEqual(contract.total_contract_value, 480.0)
        self.assertAlmostEqual(contract.monthly_value, 80.0)

    def test_onchange_date_end_by_rule_type(self):
        """Given 2 periods of interval 1 from 2026-01-15,
        When the end date onchange runs for each recurrence,
        Then date_end is the last day of the covered span."""
        contract = self._contract(
            [{"price_unit": 1.0, "period_count": 2, "date_start": "2026-01-15"}]
        )
        line = contract.contract_line_ids
        expected = {
            "daily": date(2026, 1, 16),
            "weekly": date(2026, 1, 28),
            "monthly": date(2026, 3, 14),
            "monthlylastday": date(2026, 2, 28),
            "quarterly": date(2026, 7, 14),
            "semesterly": date(2027, 1, 14),
            "yearly": date(2028, 1, 14),
        }
        for rule, end in expected.items():
            line.recurring_rule_type = rule
            line._onchange_date_start()
            self.assertEqual(line.date_end, end, rule)

    def test_monthlylastday_single_period_ends_in_start_month(self):
        """Given a monthlylastday line of 1 period starting 2026-01-15,
        When the end date is computed,
        Then it ends on the last day of January (not the day before the end of Feb)."""
        contract = self._contract(
            [
                {
                    "price_unit": 1.0,
                    "period_count": 1,
                    "recurring_rule_type": "monthlylastday",
                    "date_start": "2026-01-15",
                }
            ]
        )
        line = contract.contract_line_ids
        line._onchange_date_start()
        self.assertEqual(line.date_end, date(2026, 1, 31))

    def test_onchange_date_end_respects_interval(self):
        """Given monthly interval 2 and 3 periods,
        When date_end is computed,
        Then it spans 6 months."""
        contract = self._contract(
            [{"price_unit": 1.0, "period_count": 3, "recurring_interval": 2}]
        )
        line = contract.contract_line_ids
        line._onchange_date_start()
        self.assertEqual(line.date_end, date(2026, 6, 30))

    def test_onchange_without_start_date_is_noop(self):
        """Given a line without start date,
        When the onchange runs,
        Then date_end is unchanged."""
        # 18.0 forbids a saved line without start date (next invoice date
        # constraint), so the onchange runs on an unsaved line, as in the form
        line = self.env["contract.line"].new(
            {
                "product_id": self.product.id,
                "name": "License",
                "period_count": 2,
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
                "date_start": False,
                "date_end": date(2030, 1, 1),
            }
        )
        line._onchange_date_start()
        self.assertEqual(line.date_end, date(2030, 1, 1))

    def test_contract_totals_two_lines(self):
        """Given a monthly line (100 x 6) and a quarterly line (400 x 2),
        When contract values are computed,
        Then total = 600 + 800, average = 1400 / (6 + 6) months."""
        contract = self._contract(
            [
                {"price_unit": 50.0, "period_qty": 2.0, "period_count": 6},
                {
                    "price_unit": 400.0,
                    "period_qty": 1.0,
                    "period_count": 2,
                    "recurring_rule_type": "quarterly",
                },
            ]
        )
        self.assertAlmostEqual(contract.total_contract_value, 1400.0)
        self.assertAlmostEqual(contract.monthly_value, 1400.0 / 12, places=2)

    def test_contract_average_by_rule_type(self):
        """Given a single line of 1 period per recurrence at 120,
        When the average per period is computed,
        Then it is amount divided by the month span of the recurrence."""
        expected = {
            "daily": 120.0 * 30,
            "weekly": 120.0 * 4.33,
            "monthlylastday": 120.0,
            "semesterly": 20.0,
            "yearly": 10.0,
        }
        for rule, avg in expected.items():
            contract = self._contract(
                [
                    {
                        "price_unit": 120.0,
                        "period_count": 1,
                        "recurring_rule_type": rule,
                    }
                ]
            )
            self.assertAlmostEqual(contract.monthly_value, avg, places=1, msg=rule)

    def test_canceled_line_excluded_from_totals(self):
        """Given two lines,
        When one is canceled,
        Then it no longer counts in the contract total."""
        contract = self._contract(
            [
                {"price_unit": 100.0, "period_count": 2},
                {"price_unit": 10.0, "period_count": 2},
            ]
        )
        self.assertAlmostEqual(contract.total_contract_value, 220.0)
        contract.contract_line_ids.filtered(lambda line: line.price_unit == 10.0)[
            0
        ].cancel()
        self.assertAlmostEqual(contract.total_contract_value, 200.0)

    def test_current_period_value(self):
        """Given a line spanning 2026-01-01..2026-06-30 and next invoice in range,
        When values are computed,
        Then current value is the period amount."""
        contract = self._contract(
            [
                {
                    "price_unit": 100.0,
                    "period_qty": 2.0,
                    "period_count": 6,
                    "date_end": "2026-06-30",
                }
            ]
        )
        self.assertTrue(contract.recurring_next_date)
        self.assertAlmostEqual(contract.current_month_value, 200.0)

    def test_current_period_value_zero_out_of_range(self):
        """Given a line already finished before the next invoice date,
        When values are computed,
        Then current value is zero."""
        contract = self._contract(
            [{"price_unit": 100.0, "period_count": 1, "date_end": "2026-01-31"}]
        )
        contract.contract_line_ids.recurring_next_date = "2026-05-01"
        contract.invalidate_recordset()
        contract.contract_line_ids._compute_period_amount()
        contract._compute_period_values()
        self.assertEqual(contract.current_month_value, 0.0)

    def test_invoice_line_uses_period_amounts(self):
        """Given 3 licenses at 10 on a contract line of quantity 1,
        When the contract invoice is generated,
        Then the invoice line has quantity 3 and the subtotal 30."""
        contract = self._contract(
            [
                {
                    "price_unit": 10.0,
                    "period_qty": 3.0,
                    "period_count": 6,
                }
            ]
        )
        invoice = contract._recurring_create_invoice()
        line = invoice.invoice_line_ids
        self.assertEqual(line.quantity, 3.0)
        self.assertAlmostEqual(line.price_subtotal, 30.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 30.0)

    def test_invoice_carries_period_number_and_total(self):
        """Given a 6-period monthly contract from 2026-01-01,
        When invoice values are prepared for 2026-03-15,
        Then it is period 3 of 6."""
        contract = self._contract([{"price_unit": 10.0, "period_count": 6}])
        contract.contract_line_ids.date_end = "2026-06-30"
        vals = contract._prepare_invoice(date(2026, 3, 15))
        self.assertEqual(vals["contract_period_number"], 3)
        self.assertEqual(vals["contract_period_total"], 6)

    def test_period_number_by_rule_type(self):
        """Given 12 periods starting 2026-01-01,
        When the invoice date is 2026-07-20,
        Then the period number follows the recurrence length."""
        contract = self._contract([{"price_unit": 10.0, "period_count": 12}])
        line = contract.contract_line_ids
        line.date_end = "2036-12-31"
        # 2026-01-01 -> 2026-07-20: 200 days, 28 weeks, 6 months, 0 years
        expected = {
            "daily": 12,  # capped by period_count
            "weekly": 12,
            "monthly": 7,
            "quarterly": 3,
            "semesterly": 2,
            "yearly": 1,
        }
        for rule, number in expected.items():
            line.recurring_rule_type = rule
            vals = contract._prepare_invoice(date(2026, 7, 20))
            self.assertEqual(vals["contract_period_number"], number, rule)

    def test_period_number_capped_and_before_start(self):
        """Given 6 monthly periods,
        When invoicing far after the end or before the start,
        Then the number is capped at 6, or 0 before the start."""
        contract = self._contract([{"price_unit": 10.0, "period_count": 6}])
        contract.contract_line_ids.date_end = "2026-06-30"
        late = contract._prepare_invoice(date(2028, 1, 1))
        self.assertEqual(late["contract_period_number"], 6)
        early = contract._prepare_invoice(date(2025, 12, 1))
        self.assertEqual(early["contract_period_number"], 0)

    def test_report_action_has_line_details(self):
        """Given a contract with a discounted line,
        When the distribution report action is built,
        Then data carries per-line period and total values."""
        contract = self._contract(
            [
                {
                    "price_unit": 100.0,
                    "discount": 25.0,
                    "period_qty": 2.0,
                    "period_count": 4,
                }
            ]
        )
        action = contract.generate_period_distribution_report()
        self.assertEqual(action["type"], "ir.actions.report")
        detail = action["data"]["line_details"][0]
        self.assertAlmostEqual(detail["period_value"], 150.0)
        self.assertAlmostEqual(detail["total_line_value"], 600.0)
        self.assertAlmostEqual(action["data"]["total_value"], 600.0)
