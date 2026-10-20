# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResUsersView(TransactionCase):
    def test_agent_page_in_user_form(self):
        """A aba Agente mostra os campos de comissão no formulário do usuário."""
        arch = self.env["res.users"].get_view(
            self.env.ref("base.view_users_form").id, "form"
        )["arch"]
        tree = etree.fromstring(arch)
        for name in (
            "agent",
            "agent_type",
            "commission_id",
            "settlement",
            "salesman_as_agent",
        ):
            self.assertTrue(
                tree.xpath("//page[@name='agent_info']//field[@name='%s']" % name),
                "Campo %s ausente na aba Agente" % name,
            )

    def test_user_as_agent(self):
        """Os campos de agente do parceiro são editáveis pelo usuário."""
        commission = self.env["commission"].create({"name": "5%", "fix_qty": 5.0})
        user = self.env["res.users"].create(
            {"name": "Vendedor Teste", "login": "vendedor_userinfo_test"}
        )
        user.write(
            {
                "agent": True,
                "commission_id": commission.id,
                "salesman_as_agent": True,
                "settlement": "monthly",
            }
        )
        self.assertTrue(user.partner_id.agent)
        self.assertEqual(user.partner_id.commission_id, commission)
        self.assertTrue(user.partner_id.salesman_as_agent)
