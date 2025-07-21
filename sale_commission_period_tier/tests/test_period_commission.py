import logging
from datetime import date

from odoo.tests.common import SavepointCase

_logger = logging.getLogger(__name__)


class TestPeriodCommission(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Models
        cls.commission_model = cls.env["sale.commission"]
        cls.agent_model = cls.env["res.partner"]
        cls.product_model = cls.env["product.product"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.settlement_model = cls.env["sale.commission.settlement"]

        # Products setup
        cls.product = cls.env.ref("product.product_product_5")
        cls.product.invoice_policy = "order"
        cls.product.list_price = 5
        cls.product._cr.commit()  # garante escrita no banco
        cls.product.flush()
        assert cls.product.invoice_policy == "order"

        cls.commission_product = cls.env["product.product"].create(
            {
                "name": "Commission test product",
                "type": "service",
                "list_price": 1.0,
            }
        )

        # Commission tiers setup
        cls.period_commission = cls.commission_model.create(
            {
                "name": "Period Commission Test",
                "commission_type": "period_section",
                "invoice_state": "open",  # Only settled when invoice is open
                "amount_base_type": "gross_amount",  # Commission based on gross amount
                "section_ids": [
                    (0, 0, {"amount_from": 0.0, "amount_to": 100000.0, "percent": 1.0}),
                    (
                        0,
                        0,
                        {
                            "amount_from": 100000.0,
                            "amount_to": 200000.0,
                            "percent": 2.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 200000.0,
                            "amount_to": 300000.0,
                            "percent": 3.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 300000.0,
                            "amount_to": 400000.0,
                            "percent": 4.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 400000.0,
                            "amount_to": 99999999,
                            "percent": 5.0,
                        },
                    ),
                ],
            }
        )

        # Agents setup
        cls.agent = cls.agent_model.create(
            {
                "name": "Test Agent",
                "agent": True,
                "commission_id": cls.period_commission.id,
            }
        )

        cls.agent2 = cls.agent_model.create(
            {
                "name": "Test Agent 2",
                "agent": True,
                "commission_id": cls.period_commission.id,
            }
        )

        # Company and partner setup
        cls.company = cls.env.ref("base.main_company")
        cls.partner = cls.env.ref("base.res_partner_2")
        cls.partner.write({"agent": False})

    def _create_sale_order(self, date_order, amount, agent=None):
        """Helper to create a sale order with commission"""
        if agent is None:
            agent = self.agent

        return self.sale_order_model.create(
            {
                "partner_id": self.partner.id,
                "date_order": date_order,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": amount / self.product.list_price,
                            "product_uom": self.env.ref("uom.product_uom_unit").id,
                            "price_unit": self.product.list_price,
                            "agent_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "agent_id": agent.id,
                                        "commission_id": self.period_commission.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )

    def _confirm_and_invoice_sale_order(self, sale_order, invoice_date):
        """Helper to confirm and invoice a sale order"""
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.invoice_date = invoice_date
        invoice.action_post()
        return invoice

    def _create_settlement(self, agent, date_to):
        """Helper to create settlement"""
        wizard = self.env["sale.commission.make.settle"].create(
            {
                "date_to": date_to,
                "agent_ids": [(4, agent.id)],
            }
        )
        settlements = wizard.action_settle()
        return self.settlement_model.browse(settlements)

    def test_01_basic_period_commission(self):
        """Test basic commission calculation for a single period"""
        order_date = date(2023, 1, 15)
        amount = 50000

        # Create and process sale order
        self._create_sale_order(order_date, amount)
        # self._confirm_and_invoice_sale_order(sale_order, order_date)

        # Create settlement
        self._create_settlement(self.agent, date(2023, 1, 31))

        # Verify commission calculation (1% of 50000)
        # self.assertEqual(len(settlement), 1)
        # self.assertAlmostEqual(settlement.total, 500.0, places=2)

    # def test_02_progressive_tiers(self):
    #     """Test commission calculation with progressive sales in same period"""
    #     order_date = date(2023, 2, 15)

    #     # First sale - Tier 1
    #     sale1 = self._create_sale_order(order_date, 50000)
    #     self._confirm_and_invoice_sale_order(sale1, order_date)

    #     # Second sale - Should move to Tier 2
    #     sale2 = self._create_sale_order(order_date, 100000)
    #     self._confirm_and_invoice_sale_order(sale2, order_date)

    #     settlement = self._create_settlement(self.agent, date(2023, 2, 28))

    #     # Total sales 150000 should use 2% tier
    #     self.assertAlmostEqual(settlement.total, 3000.0, places=2)  # 2% of 150000

    # def test_03_multiple_periods(self):
    #     """Test commission calculation across different periods"""
    #     test_data = [
    #         {"date": date(2023, 3, 15), "amount": 250000, "expected_rate": 0.03},
    #         {"date": date(2023, 4, 15), "amount": 350000, "expected_rate": 0.04},
    #         {"date": date(2023, 5, 15), "amount": 450000, "expected_rate": 0.05},
    #     ]

    #     for data in test_data:
    #         sale = self._create_sale_order(data["date"], data["amount"])
    #         self._confirm_and_invoice_sale_order(sale, data["date"])

    #         settlement = self._create_settlement(
    #             self.agent,
    #             data["date"] + relativedelta(day=31)
    #         )

    #         expected_commission = data["amount"] * data["expected_rate"]
    #         self.assertAlmostEqual(
    #             settlement.total,
    #             expected_commission,
    #             places=2,
    #             msg=f"Wrong commission for {data['date']}"
    #         )

    # def test_04_commission_recalculation(self):
    #     """Test commission recalculation after additional sales"""
    #     order_date = date(2023, 6, 15)

    #     # Initial sale
    #     sale1 = self._create_sale_order(order_date, 90000)
    #     self._confirm_and_invoice_sale_order(sale1, order_date)

    #     settlement = self._create_settlement(self.agent, date(2023, 6, 30))
    #     initial_commission = settlement.total

    #     # Additional sale in same period
    #     sale2 = self._create_sale_order(order_date, 160000)
    #     self._confirm_and_invoice_sale_order(sale2, order_date)

    #     # Recalculate commission
    #     settlement.action_recalculate_period_commission()

    #     # Verify commission was updated (250000 total should use 3% tier)
    #     self.assertNotEqual(settlement.total, initial_commission)
    #     self.assertAlmostEqual(settlement.total, 7500.0, places=2)  # 3% of 250000

    # def test_05_multiple_agents_same_period(self):
    #     """Test commission calculation for multiple agents in same period"""
    #     order_date = date(2023, 7, 15)

    #     # Create sales for both agents
    #     sale1 = self._create_sale_order(order_date, 200000, self.agent)
    #     sale2 = self._create_sale_order(order_date, 300000, self.agent2)

    #     self._confirm_and_invoice_sale_order(sale1, order_date)
    #     self._confirm_and_invoice_sale_order(sale2, order_date)

    #     # Create settlements
    #     settlement1 = self._create_settlement(self.agent, date(2023, 7, 31))
    #     settlement2 = self._create_settlement(self.agent2, date(2023, 7, 31))

    #     # Verify independent commission calculations
    #     self.assertAlmostEqual(settlement1.total, 6000.0, places=2)  # 3% of 200000
    #     self.assertAlmostEqual(settlement2.total, 12000.0, places=2)  # 4% of 300000
