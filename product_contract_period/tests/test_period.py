from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductContractPeriod(TransactionCase):
    def test_period_amount(self):
        product = self.env["product.product"].create({"name": "License"})
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Customer"}).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "price_unit": 100.0,
                            "discount": 10.0,
                            "period_qty": 2.0,
                            "period_count": 3,
                        },
                    )
                ],
            }
        )
        line = order.order_line
        self.assertAlmostEqual(line.period_amount, 180.0)
        self.assertAlmostEqual(line.price_subtotal, 180.0)

    def test_product_defaults(self):
        product = self.env["product.template"].create({"name": "Plan"})
        self.assertEqual(product.default_period_qty, 1.0)
        self.assertEqual(product.default_period_count, 1)

    def test_contract_period_values(self):
        product = self.env["product.product"].create({"name": "License"})
        contract = self.env["contract.contract"].create(
            {
                "name": "Contract",
                "partner_id": self.env["res.partner"].create({"name": "Customer"}).id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "License",
                            "quantity": 1.0,
                            "price_unit": 50.0,
                            "period_qty": 2.0,
                            "period_count": 6,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2026-01-01",
                        },
                    )
                ],
            }
        )
        line = contract.contract_line_ids
        self.assertAlmostEqual(line.period_amount, 100.0)
        self.assertAlmostEqual(line.total_amount, 600.0)
        self.assertAlmostEqual(contract.total_contract_value, 600.0)
        self.assertAlmostEqual(contract.monthly_value, 100.0)
