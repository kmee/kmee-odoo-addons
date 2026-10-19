# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPeriodCommission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.commission = cls.env["commission"].create(
            {
                "name": "Period tiers",
                "commission_type": "period_section",
                "invoice_state": "open",
                "amount_base_type": "gross_amount",
                "section_ids": [
                    (0, 0, {"amount_from": 0.0, "amount_to": 1000.0, "percent": 1.0}),
                    (
                        0,
                        0,
                        {"amount_from": 1000.01, "amount_to": 2000.0, "percent": 2.0},
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 2000.01,
                            "amount_to": 99999999.0,
                            "percent": 3.0,
                        },
                    ),
                ],
            }
        )
        cls.agent = cls.env["res.partner"].create(
            {
                "name": "Agent Period",
                "agent": True,
                "settlement": "monthly",
                "commission_id": cls.commission.id,
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Customer Period"})
        cls.product = cls.env["product.product"].create(
            {"name": "Product Period", "list_price": 100.0, "standard_price": 40.0}
        )

    def _invoice(self, amount, invoice_date, move_type="out_invoice", qty=1.0):
        invoice = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.customer.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": qty,
                            "price_unit": amount / qty,
                            "agent_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "agent_id": self.agent.id,
                                        "commission_id": self.commission.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _settle(self, date_to=None):
        wizard = self.env["commission.make.settle"].create(
            {
                "date_to": date_to or date(2024, 2, 15),
                "agent_ids": [(4, self.agent.id)],
                "settlement_type": "sale_invoice",
            }
        )
        action = wizard.action_settle()
        return self.env["commission.settlement"].search(action["domain"])

    def test_calculate_period_section(self):
        self.assertEqual(self.commission.calculate_period_section(), 1.0)
        self.assertEqual(self.commission.calculate_period_section(500), 1.0)
        self.assertEqual(self.commission.calculate_period_section(1000), 1.0)
        self.assertEqual(self.commission.calculate_period_section(1500), 2.0)
        self.assertEqual(self.commission.calculate_period_section(999999), 3.0)
        # no section contains the total (negative period)
        self.assertEqual(self.commission.calculate_period_section(-10), 0.0)

    def test_calculate_period_section_other_type(self):
        fixed = self.env["commission"].create({"name": "Fixed", "fix_qty": 5.0})
        self.assertEqual(fixed.calculate_period_section(500), 0.0)

    def test_invoice_line_provisional_amount(self):
        """Before the settlement the rate of the first tier is used."""
        invoice = self._invoice(500.0, date(2024, 1, 10))
        self.assertAlmostEqual(invoice.invoice_line_ids.agent_ids.amount, 5.0)

    def test_single_invoice_first_tier(self):
        self._invoice(500.0, date(2024, 1, 10))
        settlement = self._settle()
        self.assertAlmostEqual(settlement.total, 5.0)

    def test_tier_reached_by_period_total(self):
        """The rate of the tier of the sum of the invoices applies to all lines."""
        self._invoice(500.0, date(2024, 1, 10))
        self._invoice(700.0, date(2024, 1, 20))
        settlement = self._settle()
        self.assertEqual(len(settlement.line_ids), 2)
        # total 1200 -> 2% on every line
        self.assertAlmostEqual(
            sorted(settlement.line_ids.mapped("settled_amount")), [10.0, 14.0]
        )
        self.assertAlmostEqual(settlement.total, 24.0)

    def test_last_tier(self):
        self._invoice(3000.0, date(2024, 1, 10))
        self.assertAlmostEqual(self._settle().total, 90.0)

    def test_invoices_of_other_period_do_not_add_up(self):
        self._invoice(1500.0, date(2024, 1, 10))
        self._invoice(1500.0, date(2024, 2, 10))
        settlements = self._settle(date_to=date(2024, 3, 15))
        self.assertEqual(len(settlements), 2)
        # each month has its own total: 1500 -> 2% in both
        self.assertEqual(settlements.mapped("total"), [30.0, 30.0])

    def test_total_counts_each_invoice_line_once(self):
        """An invoice with several lines does not count its total once per line."""
        invoice = self._invoice(600.0, date(2024, 1, 10), qty=3.0)
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertAlmostEqual(self._settle().total, 6.0)

    def test_refund_reduces_the_total(self):
        self._invoice(1500.0, date(2024, 1, 10))
        self._invoice(600.0, date(2024, 1, 15), move_type="out_refund")
        settlement = self._settle()
        # total 900 -> 1%: 15.0 of the invoice and -6.0 of the refund
        self.assertAlmostEqual(
            sorted(settlement.line_ids.mapped("settled_amount")), [-6.0, 15.0]
        )

    def test_net_amount_base(self):
        """Margin based commission: the cost of the product is discounted."""
        self.commission.amount_base_type = "net_amount"
        self._invoice(1000.0, date(2024, 1, 10), qty=10.0)
        # base = 1000 - 40 * 10 = 600 -> first tier (1%)
        self.assertAlmostEqual(self._settle().total, 6.0)

    def test_commission_free_product(self):
        self.product.commission_free = True
        self._invoice(500.0, date(2024, 1, 10))
        settlement = self._settle()
        self.assertAlmostEqual(settlement.total, 0.0)

    def test_second_settlement_run_recalculates_whole_period(self):
        self._invoice(600.0, date(2024, 1, 10))
        settlement = self._settle()
        self.assertAlmostEqual(settlement.total, 6.0)
        self._invoice(600.0, date(2024, 1, 25))
        settlement_2 = self._settle()
        self.assertEqual(settlement, settlement_2)
        # total 1200 -> 2% on both lines, including the one already settled
        self.assertAlmostEqual(settlement.total, 24.0)

    def test_recalculate_button(self):
        self._invoice(600.0, date(2024, 1, 10))
        settlement = self._settle()
        settlement.line_ids.settled_amount = 0.0
        settlement.action_recalculate_period_commission()
        self.assertAlmostEqual(settlement.total, 6.0)

    def test_cancelled_settlement_is_not_recalculated(self):
        self._invoice(600.0, date(2024, 1, 10))
        settlement = self._settle()
        settlement.action_cancel()
        settlement.line_ids.settled_amount = 1.0
        settlement.recalculate_period_commission()
        self.assertAlmostEqual(settlement.total, 1.0)

    def test_other_commission_types_untouched(self):
        fixed = self.env["commission"].create({"name": "Fixed", "fix_qty": 10.0})
        self.agent.commission_id = fixed
        invoice = self._invoice(500.0, date(2024, 1, 10))
        invoice.invoice_line_ids.agent_ids.commission_id = fixed
        invoice.invoice_line_ids.agent_ids._compute_amount()
        settlement = self._settle()
        self.assertAlmostEqual(settlement.total, 50.0)
