# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSettlementManualInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.agent = cls.env["res.partner"].create({"name": "Agent", "agent": True})
        cls.settlement = cls.env["commission.settlement"].create(
            {
                "agent_id": cls.agent.id,
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
            }
        )

    def test_automatic_invoicing_disabled(self):
        with self.assertRaises(UserError):
            self.settlement.action_invoice()
        product = self.env["product.product"].create({"name": "Commission"})
        journal = self.env["account.journal"].search(
            [("type", "=", "purchase")], limit=1
        )
        with self.assertRaises(UserError):
            self.settlement.make_invoices(journal, product)

    def test_manual_flow(self):
        self.assertEqual(self.settlement.state, "settled")
        self.settlement.action_mark_invoiced()
        self.assertEqual(self.settlement.state, "invoiced")
        self.settlement.action_confirm()
        self.assertEqual(self.settlement.state, "paid")
        self.settlement.action_settle()
        self.assertEqual(self.settlement.state, "settled")

    def test_invoice_exception_and_cancel(self):
        self.settlement.action_mark_invoiced()
        self.settlement.action_except_invoice()
        self.assertEqual(self.settlement.state, "except_invoice")
        # without generated invoice an invoiced settlement can be cancelled
        self.settlement.action_cancel()
        self.assertEqual(self.settlement.state, "cancel")

    def test_settlement_form_view(self):
        arch = self.env["commission.settlement"].get_view(
            self.env.ref("account_commission.view_settlement_form").id, "form"
        )["arch"]
        tree = etree.fromstring(arch)
        for name in (
            "action_mark_invoiced",
            "action_confirm",
            "action_except_invoice",
            "action_settle",
        ):
            self.assertTrue(tree.xpath("//button[@name='%s']" % name), name)
        self.assertFalse(tree.xpath("//button[@name='action_invoice']"))

    def test_make_invoice_menu_hidden(self):
        menu = self.env.ref("account_commission.menu_invoicing_settlements")
        self.assertFalse(menu.active)
