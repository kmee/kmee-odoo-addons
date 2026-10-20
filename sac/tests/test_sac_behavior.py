# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestSacBehavior(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        cls.sac_model = cls.env["sac"]
        cls.stage_new = cls.env.ref("sac.sac_kanban_new")
        cls.stage_analysis = cls.env.ref("sac.sac_kanban_analisado")
        cls.stage_shipping = cls.env.ref("sac.sac_kanban_aguardando_envio")
        cls.stage_solved = cls.env.ref("sac.sac_kanban_solucionado")
        cls.group_read = cls.env.ref("sac.GROUP_SAC_READ")
        cls.group_general = cls.env.ref("sac.GROUP_SAC_GENERAL")
        cls.group_manager = cls.env.ref("sac.GROUP_SAC_MANAGER")

    @classmethod
    def _user(cls, login, group):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, group.id])],
            }
        )

    def _sac(self, **vals):
        vals.setdefault("customer_name", "Maria Cliente")
        return self.sac_model.create(vals)

    # ------------------------------------------------------------------
    # Creation, sequence, names
    # ------------------------------------------------------------------
    def test_create_assigns_sequence_stage_and_defaults(self):
        """Given no values besides the customer, When creating a SAC, Then it
        gets the next SAC sequence, the first stage, qty 1, rating 0 and the
        creator as responsible."""
        first = self._sac()
        second = self._sac()
        self.assertRegex(first.name, r"^SAC/\d+$")
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(first.stage_id, self.stage_new)
        self.assertEqual((first.qty, first.rating), (1, "0"))
        self.assertEqual(first.user_id, self.env.user)
        self.assertTrue(first.active)

    def test_create_with_company_uses_company_sequence(self):
        """Given a company with its own SAC sequence, When creating a SAC for
        that company, Then the number comes from the company sequence."""
        company = self.env["res.company"].create({"name": "Other SAC Co"})
        self.env["ir.sequence"].create(
            {
                "name": "SAC other",
                "code": "sac",
                "prefix": "OTH/",
                "padding": 2,
                "company_id": company.id,
            }
        )
        sac = self._sac(company_id=company.id)
        self.assertEqual(sac.name, "OTH/01")
        self.assertTrue(self._sac().name.startswith("SAC/"))

    def test_create_without_sequence_falls_back_to_new(self):
        """Given no sequence for the code, When creating, Then the name is
        'New' instead of failing."""
        self.env["ir.sequence"].search([("code", "=", "sac")]).unlink()
        self.assertEqual(self._sac().name, "New")

    def test_name_get_and_search_by_customer(self):
        """Given a SAC of customer Maria, Then its display name has the
        reference and the customer, and it is found by customer name."""
        sac = self._sac(customer_name="Maria Zebra")
        self.assertEqual(sac.name_get(), [(sac.id, "%s - Maria Zebra" % sac.name)])
        found = self.sac_model.name_search("Zebra")
        self.assertIn(sac.id, [rec[0] for rec in found])
        self.assertFalse(self.sac_model.name_search("Nobody-Here-X"))

    def test_name_get_without_customer_is_the_reference(self):
        """Given a SAC whose customer name was cleared, Then name_get is just
        the reference."""
        sac = self._sac()
        sac.customer_name = False
        self.assertEqual(sac.name_get(), [(sac.id, sac.name)])

    def test_customer_name_is_required(self):
        """Given no customer name, Then the SAC cannot be created."""
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError), (
            self.cr.savepoint()
        ):
            self.sac_model.create({"email_from": "x@example.com"})

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------
    def test_price_total_is_price_times_quantity(self):
        """Given a product of 25.0 and qty 3, Then total is 75.0; without
        product or without quantity the total is zero."""
        product = self.env["product.product"].create(
            {"name": "SAC Product", "list_price": 25.0, "sac_ok": True}
        )
        sac = self._sac(product_id=product.id, qty=3)
        self.assertEqual(sac.price, 25.0)
        self.assertEqual(sac.price_total, 75.0)
        sac.qty = 0
        self.assertEqual(sac.price_total, 0.0)
        self.assertEqual(self._sac().price_total, 0.0)

    def test_create_date_date_follows_create_date(self):
        """Given a saved SAC, Then create_date_date is the creation day."""
        sac = self._sac()
        self.assertEqual(sac.create_date_date, sac.create_date.date())

    def test_kanban_color_follows_the_reason(self):
        """Given a reason with color 9, When it is set on the SAC, Then the
        stored kanban color is 9 and it follows later changes."""
        reason = self.env["sac.reason"].create({"name": "Orange", "kanban_color": "9"})
        sac = self._sac(reason_id=reason.id)
        self.assertEqual(sac.kanban_color, "9")
        reason.kanban_color = "7"
        self.assertEqual(sac.kanban_color, "7")
        self.assertEqual(self.env["sac.reason"].create({"name": "d"}).kanban_color, "2")

    def test_product_flag_sac_ok_defaults_to_false(self):
        """Given a new product, Then it is not visible to the SAC until
        flagged."""
        product = self.env["product.template"].create({"name": "Plain"})
        self.assertFalse(product.sac_ok)

    # ------------------------------------------------------------------
    # Stages, mail and recipients
    # ------------------------------------------------------------------
    def test_seeded_stages_and_templates(self):
        """Given the seed data, Then the analysis stage sends the 'received'
        template, the new stage sends nothing, and solved stages are folded."""
        self.assertEqual(
            self.stage_analysis.mail_template_id,
            self.env.ref("sac.mail_template_sac_receive"),
        )
        self.assertFalse(self.stage_new.mail_template_id)
        self.assertTrue(self.stage_solved.fold)
        self.assertTrue(self.env.ref("sac.sac_kanban_nao_solucionado").fold)
        self.assertFalse(self.stage_shipping.fold)

    def test_stage_change_with_template_posts_mail_to_customer(self):
        """Given a SAC with customer e-mail, When it moves to the analysis
        stage (which has a template), Then a message with the template content
        is posted; moving to a stage without template posts no such message."""
        sac = self.sac_model.with_context(
            tracking_disable=False, mail_notrack=False
        ).create({"customer_name": "Maria Cliente", "email_from": "maria@example.com"})
        sac.write({"stage_id": self.stage_shipping.id})
        self.env.cr.precommit.run()
        self.assertNotIn(
            "recebemos o seu chamado", " ".join(sac.message_ids.mapped("body"))
        )
        sac.write({"stage_id": self.stage_analysis.id})
        self.env.cr.precommit.run()
        bodies = " ".join(sac.message_ids.mapped("body"))
        self.assertIn("recebemos o seu chamado", bodies)
        self.assertIn("Maria Cliente", bodies)

    def test_track_template_only_reacts_to_stage_changes(self):
        """Given a SAC in the analysis stage, Then the template is returned for
        a stage change and nothing for other tracked fields."""
        sac = self._sac(stage_id=self.stage_analysis.id)
        self.assertEqual(
            sac._track_template(["stage_id"])["stage_id"][0],
            self.stage_analysis.mail_template_id,
        )
        self.assertEqual(sac._track_template(["phone"]), {})
        sac.stage_id = self.stage_new
        self.assertEqual(sac._track_template(["stage_id"]), {})

    def test_suggested_recipients_include_customer_email(self):
        """Given a SAC with e-mail, Then the customer is a suggested recipient;
        without e-mail there is none."""
        sac = self._sac(email_from="maria@example.com")
        emails = [r[1] for r in sac._message_get_suggested_recipients()[sac.id]]
        self.assertIn("maria@example.com", emails)
        other = self._sac()
        emails = [r[1] for r in other._message_get_suggested_recipients()[other.id]]
        self.assertNotIn("maria@example.com", emails)

    def test_email_split_collects_to_cc_and_from(self):
        """Given a message dict, Then all addresses of to, cc and from are
        returned, ignoring names."""
        sac = self._sac()
        msg = {
            "to": "a@example.com",
            "cc": "Bob <b@example.com>",
            "from": "c@example.com",
        }
        self.assertEqual(
            sorted(sac.email_split(msg)),
            ["a@example.com", "b@example.com", "c@example.com"],
        )

    # ------------------------------------------------------------------
    # Deletion rule
    # ------------------------------------------------------------------
    def test_sac_in_open_stage_can_be_deleted_by_manager(self):
        """Given a SAC in an open stage, When a SAC manager deletes it, Then it
        is deleted."""
        manager = self._user("sac_mgr_del", self.group_manager)
        sac = self._sac()
        sac.with_user(manager).unlink()
        self.assertFalse(sac.exists())

    def test_sac_in_done_stage_cannot_be_deleted(self):
        """Given a SAC in the solved stage, When deleting it, Then UserError
        and the record stays."""
        sac = self._sac(stage_id=self.stage_solved.id)
        with self.assertRaises(UserError):
            sac.unlink()
        self.assertTrue(sac.exists())

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    def test_groups_are_hierarchical(self):
        """Given the SAC groups, Then manager implies general and general
        implies read-only."""
        self.assertIn(self.group_read, self.group_general.implied_ids)
        self.assertIn(self.group_general, self.group_manager.implied_ids)

    def test_read_group_cannot_create_or_write(self):
        """Given a read-only SAC user, Then reading works, creating and writing
        are denied."""
        reader = self._user("sac_reader", self.group_read)
        sac = self._sac()
        self.assertEqual(sac.with_user(reader).customer_name, "Maria Cliente")
        with self.assertRaises(AccessError):
            sac.with_user(reader).write({"customer_name": "Hacked"})
        with self.assertRaises(AccessError):
            self.sac_model.with_user(reader).create({"customer_name": "Hacked"})

    def test_general_group_creates_and_writes_but_cannot_delete(self):
        """Given a general SAC user, Then create/write work but delete is
        denied (only managers delete)."""
        general = self._user("sac_general", self.group_general)
        sac = self.sac_model.with_user(general).create({"customer_name": "Ana"})
        sac.write({"phone": "123"})
        self.assertEqual(sac.phone, "123")
        with self.assertRaises(AccessError):
            sac.unlink()

    def test_kanban_grouping_by_stage_works_for_sac_users(self):
        """Given a read-only SAC user, When the kanban groups SACs by stage,
        Then all SAC stages are returned even for empty columns."""
        reader = self._user("sac_kanban", self.group_read)
        self._sac()
        groups = self.sac_model.with_user(reader).read_group(
            [], ["stage_id"], ["stage_id"]
        )
        stages = {g["stage_id"][0] for g in groups}
        self.assertIn(self.stage_new.id, stages)
        self.assertIn(self.stage_solved.id, stages)

    def test_user_without_sac_group_has_no_access(self):
        """Given an internal user outside the SAC groups, Then reading is
        denied."""
        outsider = self.env["res.users"].create(
            {
                "name": "Outsider",
                "login": "sac_outsider",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self._sac().with_user(outsider).read(["customer_name"])

    # ------------------------------------------------------------------
    # Print wizard
    # ------------------------------------------------------------------
    def test_print_wizard_without_pending_returns_false(self):
        """Given no SAC waiting for shipping, When the wizard runs, Then it
        returns False."""
        self.sac_model.search([]).unlink()
        wizard = self.env["sac.print"].create({"name": "x"})
        self.assertFalse(wizard.doit())

    def test_print_wizard_with_pending_needs_the_report(self):
        """Given SACs waiting for shipping and no declaration report installed,
        When printing, Then a clear UserError is raised and nothing is marked as
        printed (a SAC in analysis is never touched either)."""
        pending = self._sac(stage_id=self.stage_shipping.id)
        other = self._sac(stage_id=self.stage_analysis.id)
        wizard = self.env["sac.print"].create({"name": "x"})
        with self.assertRaises(UserError):
            wizard.doit()
        self.assertFalse(pending.is_printed)
        self.assertFalse(other.is_printed)

    def test_print_wizard_marks_only_shipping_stage_as_printed(self):
        """Given the report exists, When printing, Then only the shipping SACs
        are marked printed, once, and the report action is returned."""
        pending = self._sac(stage_id=self.stage_shipping.id)
        printed = self._sac(stage_id=self.stage_shipping.id, is_printed=True)
        other = self._sac(stage_id=self.stage_analysis.id)
        report = self.env["ir.actions.report"].create(
            {
                "name": "Declaracao",
                "model": "sac",
                "report_type": "qweb-pdf",
                "report_name": "sac.sac_declaracao_conteudo",
            }
        )
        self.env.company.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        )
        wizard = self.env["sac.print"].create({"name": "x"})
        action = wizard.doit()
        self.assertTrue(pending.is_printed)
        self.assertTrue(printed.is_printed)
        self.assertFalse(other.is_printed)
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], report.report_name)
        self.assertEqual(action["context"]["active_ids"], pending.ids)
        self.assertFalse(wizard.doit())
