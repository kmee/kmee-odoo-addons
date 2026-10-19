# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class ContractPeriodCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
                no_reset_password=True,
            )
        )
        cls.template = cls.env["contract.template"].create({"name": "Template"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "License",
                "type": "service",
                "is_contract": True,
                "list_price": 100.0,
                "property_contract_template_id": cls.template.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})

    def _order(self, lines):
        """lines: list of dicts merged over sane defaults."""
        vals = {
            "partner_id": self.partner.id,
            "order_line": [
                (
                    0,
                    0,
                    dict(
                        {
                            "product_id": self.product.id,
                            "date_start": "2026-01-01",
                        },
                        **line,
                    ),
                )
                for line in lines
            ],
        }
        if "fiscal_operation_id" in self.env["sale.order"]._fields:
            vals["fiscal_operation_id"] = False
        return self.env["sale.order"].create(vals)

    def _contract(self, lines):
        return self.env["contract.contract"].create(
            {
                "name": "Contract",
                "partner_id": self.partner.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        dict(
                            {
                                "product_id": self.product.id,
                                "name": "License",
                                "quantity": 1.0,
                                "recurring_rule_type": "monthly",
                                "recurring_interval": 1,
                                "date_start": "2026-01-01",
                            },
                            **line,
                        ),
                    )
                    for line in lines
                ],
            }
        )
