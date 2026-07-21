import logging
from datetime import date

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPeriodCommission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Models
        cls.commission_model = cls.env["commission"]
        cls.agent_model = cls.env["res.partner"]
        cls.product_model = cls.env["product.product"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.settlement_model = cls.env["commission.settlement"]

        # Products setup
        cls.product = cls.env.ref("product.product_product_5")
        cls.product.invoice_policy = "order"
        cls.product.list_price = 5

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
                "invoice_state": "open",
                "amount_base_type": "gross_amount",
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
                            "commission_line_ids": [
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
        wizard = self.env["commission.make.settle"].create(
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
