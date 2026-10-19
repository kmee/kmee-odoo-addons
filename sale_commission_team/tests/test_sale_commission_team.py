# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleCommissionTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        Commission = cls.env["commission"]
        cls.commission_10 = Commission.create({"name": "10%", "fix_qty": 10.0})
        cls.commission_5 = Commission.create({"name": "5%", "fix_qty": 5.0})
        cls.commission_2 = Commission.create({"name": "2%", "fix_qty": 2.0})
        Partner = cls.env["res.partner"]
        cls.agent_team = Partner.create(
            {"name": "Agent Team", "agent": True, "commission_id": cls.commission_10.id}
        )
        cls.agent_partner = Partner.create(
            {
                "name": "Agent Partner",
                "agent": True,
                "commission_id": cls.commission_5.id,
            }
        )
        cls.agent_team_partner = Partner.create(
            {"name": "Agent TP", "agent": True, "commission_id": cls.commission_2.id}
        )
        cls.agent_salesman = Partner.create(
            {
                "name": "Agent Salesman",
                "agent": True,
                "salesman_as_agent": True,
                "commission_id": cls.commission_2.id,
            }
        )
        cls.salesman = cls.env["res.users"].create(
            {
                "name": "Salesman",
                "login": "salesman_commission_team",
                "partner_id": cls.agent_salesman.id,
            }
        )
        cls.team = cls.env["crm.team"].create({"name": "Team Commission"})
        cls.env["crm.team.agent"].create(
            {
                "team_id": cls.team.id,
                "agent_id": cls.agent_team.id,
                "commission_id": cls.commission_10.id,
            }
        )
        cls.customer = Partner.create(
            {"name": "Customer", "agent_ids": [(6, 0, cls.agent_partner.ids)]}
        )
        cls.env["res.partner.agent.team"].create(
            {
                "partner_id": cls.customer.id,
                "team_id": cls.team.id,
                "agent_id": cls.agent_team_partner.id,
                "commission_id": cls.commission_2.id,
            }
        )
        cls.rule_team = cls.env.ref("sale_commission_team.commission_rule_team")
        cls.rule_team_partner = cls.env.ref(
            "sale_commission_team.commission_rule_team_partner"
        )
        cls.rule_partner = cls.env.ref("sale_commission_team.commission_rule_partner")
        cls.rule_salesman = cls.env.ref("sale_commission_team.commission_rule_salesman")
        cls.product = cls.env["product.product"].create(
            {"name": "Product", "list_price": 100.0}
        )

    def _create_order(self, team=None, user=None):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "team_id": team.id if team else False,
                "user_id": user.id if user else False,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )

    def _create_invoice(self, team=None, user=None):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "team_id": team.id if team else False,
                "invoice_user_id": user.id if user else False,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )

    def _agents(self, line):
        return line.agent_ids.mapped("agent_id")

    def test_rules_team_and_partner(self):
        self.team.commission_rule_ids = self.rule_team + self.rule_partner
        order = self._create_order(team=self.team)
        self.assertEqual(
            self._agents(order.order_line), self.agent_team + self.agent_partner
        )

    def test_rules_all(self):
        self.team.commission_rule_ids = (
            self.rule_team + self.rule_team_partner + self.rule_partner
        )
        order = self._create_order(team=self.team)
        self.assertEqual(
            self._agents(order.order_line),
            self.agent_team + self.agent_team_partner + self.agent_partner,
        )

    def test_rule_team_partner_only(self):
        self.team.commission_rule_ids = self.rule_team_partner
        order = self._create_order(team=self.team)
        self.assertEqual(self._agents(order.order_line), self.agent_team_partner)
        line_agent = order.order_line.agent_ids
        self.assertEqual(line_agent.commission_id, self.commission_2)

    def test_rule_salesman(self):
        self.team.commission_rule_ids = self.rule_salesman
        order = self._create_order(team=self.team, user=self.salesman)
        self.assertEqual(self._agents(order.order_line), self.agent_salesman)

    def test_agent_not_duplicated(self):
        """The same agent returned by two rules is added only once."""
        self.env["crm.team.agent"].create(
            {
                "team_id": self.team.id,
                "agent_id": self.agent_partner.id,
                "commission_id": self.commission_10.id,
            }
        )
        self.team.commission_rule_ids = self.rule_team + self.rule_partner
        order = self._create_order(team=self.team)
        self.assertEqual(len(order.order_line.agent_ids), 2)
        # the first rule wins: the commission of the team is used
        agent_line = order.order_line.agent_ids.filtered(
            lambda a: a.agent_id == self.agent_partner
        )
        self.assertEqual(agent_line.commission_id, self.commission_10)

    def test_rules_sequence(self):
        self.rule_partner.sequence = 5
        self.team.commission_rule_ids = self.rule_team + self.rule_partner
        order = self._create_order(team=self.team)
        self.assertEqual(
            order.order_line.agent_ids.mapped("agent_id"),
            self.agent_partner + self.agent_team,
        )
        self.assertEqual(order.order_line.agent_ids[0].agent_id, self.agent_partner)

    def test_team_without_rules_has_no_agents(self):
        self.team.commission_rule_ids = False
        order = self._create_order(team=self.team)
        self.assertFalse(order.order_line.agent_ids)

    def test_without_team_default_behavior(self):
        order = self._create_order()
        self.assertEqual(self._agents(order.order_line), self.agent_partner)

    def test_change_team_recomputes_agents(self):
        self.team.commission_rule_ids = self.rule_team
        order = self._create_order()
        self.assertEqual(self._agents(order.order_line), self.agent_partner)
        order.team_id = self.team
        self.assertEqual(self._agents(order.order_line), self.agent_team)

    def test_invoice_line_with_team(self):
        self.team.commission_rule_ids = self.rule_team + self.rule_partner
        invoice = self._create_invoice(team=self.team)
        self.assertEqual(
            self._agents(invoice.invoice_line_ids),
            self.agent_team + self.agent_partner,
        )

    def test_invoice_line_without_team(self):
        invoice = self._create_invoice()
        self.assertEqual(self._agents(invoice.invoice_line_ids), self.agent_partner)

    def test_commission_free_product(self):
        self.product.commission_free = True
        self.team.commission_rule_ids = self.rule_team
        order = self._create_order(team=self.team)
        self.assertFalse(order.order_line.agent_ids)
