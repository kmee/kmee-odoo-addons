# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import new_test_user


class TierExceptionsMixin:
    """Fixtures shared by the model and the controller tests."""

    @classmethod
    def _setup_tier_exceptions(cls):
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.approver = new_test_user(
            cls.env,
            login="tier_exc_approver",
            groups="base.group_user,sales_team.group_sale_manager,"
            "base_exception.group_exception_rule_manager",
        )
        cls.salesman = new_test_user(
            cls.env,
            login="tier_exc_salesman",
            groups="base.group_user,sales_team.group_sale_salesman_all_leads",
        )
        cls.tier = cls.env.ref(
            "sale_tier_validation_exceptions.sales_order_exceptions_approver"
        )
        cls.tier.write({"review_type": "individual", "reviewer_id": cls.approver.id})
        cls.rule = cls.env["exception.rule"].create(
            {
                "name": "Big order",
                "model": "sale.order",
                "exception_type": "by_domain",
                "domain": "[('amount_untaxed', '>', 1000)]",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create(
            # a service: no stock procurement written on the order after validation
            {"name": "Product", "list_price": 1.0, "type": "service"}
        )

    def _order(self, price_unit):
        vals = {
            "partner_id": self.partner.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 1.0,
                        "price_unit": price_unit,
                    },
                )
            ],
        }
        if "order_sequence" in self.env["sale.order"]._fields:
            # isolated quotation (when installed in the same database) turns
            # action_confirm of a quotation into a wizard: flag it as an order
            vals["order_sequence"] = True
        return self.env["sale.order"].create(vals)
