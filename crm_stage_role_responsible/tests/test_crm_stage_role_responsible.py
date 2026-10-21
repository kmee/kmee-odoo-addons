# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmStageRoleResponsible(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.owner = Users.create({"name": "Owner", "login": "role_owner"})
        cls.sdr = Users.create({"name": "SDR", "login": "role_sdr"})
        cls.hunter = Users.create({"name": "Hunter", "login": "role_hunter"})
        cls.closer = Users.create({"name": "Closer", "login": "role_closer"})
        cls.farmer = Users.create({"name": "Farmer", "login": "role_farmer"})
        cls.users = cls.owner | cls.sdr | cls.hunter | cls.closer | cls.farmer
        cls.team = cls.env["crm.team"].create(
            {"name": "Role team", "member_ids": [(6, 0, cls.users.ids)]}
        )
        Stage = cls.env["crm.stage"]
        cls.stage_plain = Stage.create({"name": "Role plain"})
        cls.stage_sdr = Stage.create(
            {"name": "Role SDR", "role_responsible": "sdr_bdr"}
        )
        cls.stage_hunter = Stage.create(
            {"name": "Role hunter", "role_responsible": "hunter"}
        )
        cls.stage_closer = Stage.create(
            {"name": "Role closer", "role_responsible": "closer"}
        )
        cls.stage_farmer = Stage.create(
            {"name": "Role farmer", "role_responsible": "farmer"}
        )
        cls.Lead = cls.env["crm.lead"]

    def _vals(self, stage, **extra):
        vals = {
            "name": "Role lead",
            "type": "opportunity",
            "team_id": self.team.id,
            "user_id": self.owner.id,
            "stage_id": stage.id,
        }
        vals.update(extra)
        return vals

    def _roles(self):
        return {
            "sdr_bdr_id": self.sdr.id,
            "hunter_id": self.hunter.id,
            "closer_id": self.closer.id,
            "farmer_id": self.farmer.id,
        }

    # stage ----------------------------------------------------------------

    def test_stage_role_defaults_to_default(self):
        """Given a new stage, the responsible role is default."""
        self.assertEqual(self.stage_plain.role_responsible, "default")

    # assignment by role -------------------------------------------------------

    def test_default_stage_keeps_the_salesperson(self):
        """Given a default stage, the lead owner is untouched."""
        lead = self.Lead.create(self._vals(self.stage_plain, **self._roles()))
        self.assertEqual(lead.user_id, self.owner)

    def test_each_role_stage_assigns_its_role_user_on_create(self):
        """Given a role stage, creating the lead makes that role the responsible."""
        for stage, user in (
            (self.stage_sdr, self.sdr),
            (self.stage_hunter, self.hunter),
            (self.stage_closer, self.closer),
            (self.stage_farmer, self.farmer),
        ):
            with self.subTest(role=stage.role_responsible):
                lead = self.Lead.create(self._vals(stage, **self._roles()))
                self.assertEqual(lead.user_id, user)

    def test_moving_to_role_stage_reassigns_responsible(self):
        """Given a lead in a plain stage, moving to Hunter makes the hunter responsible."""
        lead = self.Lead.create(self._vals(self.stage_plain, **self._roles()))
        lead.write({"stage_id": self.stage_hunter.id})
        self.assertEqual(lead.user_id, self.hunter)
        lead.write({"stage_id": self.stage_closer.id})
        self.assertEqual(lead.user_id, self.closer)

    def test_moving_back_to_default_stage_keeps_last_responsible(self):
        """Given a lead assigned by role, going to a default stage does not unassign."""
        lead = self.Lead.create(self._vals(self.stage_closer, **self._roles()))
        lead.write({"stage_id": self.stage_plain.id})
        self.assertEqual(lead.user_id, self.closer)

    def test_role_stage_without_role_user_is_refused_on_create(self):
        """Given a closer stage and no closer, creating the lead is refused."""
        with self.assertRaises(UserError) as error:
            self.Lead.create(self._vals(self.stage_closer, sdr_bdr_id=self.sdr.id))
        self.assertIn("CLOSER", str(error.exception))

    def test_moving_to_role_stage_without_role_user_is_refused(self):
        """Given a lead without a farmer, moving it to the farmer stage is refused."""
        lead = self.Lead.create(self._vals(self.stage_plain))
        with self.assertRaises(UserError) as error:
            lead.write({"stage_id": self.stage_farmer.id})
        self.assertIn("FARMER", str(error.exception))

    def test_refusal_message_names_composite_role(self):
        """Given the SDR/BDR stage, the refusal names the role as SDR/BDR."""
        with self.assertRaises(UserError) as error:
            self.Lead.create(self._vals(self.stage_sdr))
        self.assertIn("SDR/BDR", str(error.exception))

    def test_type_change_triggers_the_role_check(self):
        """Given a lead in a role stage, converting type re-applies the role."""
        lead = self.Lead.create(
            self._vals(self.stage_closer, type="lead", **self._roles())
        )
        lead.user_id = self.owner
        lead.write({"type": "opportunity"})
        self.assertEqual(lead.user_id, self.closer)

    def test_unrelated_write_does_not_reassign(self):
        """Given a lead in a role stage, editing the name keeps a manual reassignment."""
        lead = self.Lead.create(self._vals(self.stage_closer, **self._roles()))
        lead.user_id = self.owner
        lead.write({"name": "Renamed"})
        self.assertEqual(lead.user_id, self.owner)

    def test_batch_create_assigns_each_lead(self):
        """Given two leads created together, each gets its own role user."""
        leads = self.Lead.create(
            [
                self._vals(self.stage_hunter, name="One", **self._roles()),
                self._vals(
                    self.stage_farmer,
                    name="Two",
                    **dict(self._roles(), farmer_id=self.owner.id),
                ),
            ]
        )
        self.assertEqual(leads[0].user_id, self.hunter)
        self.assertEqual(leads[1].user_id, self.owner)

    def test_batch_stage_change_assigns_each_lead(self):
        """Given two leads, moving both to the closer stage assigns their closers."""
        one = self.Lead.create(self._vals(self.stage_plain, name="A", **self._roles()))
        two = self.Lead.create(
            self._vals(
                self.stage_plain,
                name="B",
                **dict(self._roles(), closer_id=self.owner.id),
            )
        )
        (one | two).write({"stage_id": self.stage_closer.id})
        self.assertEqual(one.user_id, self.closer)
        self.assertEqual(two.user_id, self.owner)

    # team flags ----------------------------------------------------------------

    def test_hide_flags_follow_the_team(self):
        """Given a team hiding the hunter, its leads mirror the flags."""
        self.team.write({"hide_hunter": True, "hide_sdr_bdr": True})
        lead = self.Lead.create(self._vals(self.stage_plain))
        self.assertTrue(lead.hide_hunter)
        self.assertTrue(lead.hide_sdr_bdr)
        self.assertFalse(lead.hide_farmer)
        self.assertFalse(lead.hide_closer)
        self.team.hide_hunter = False
        self.assertFalse(lead.hide_hunter)

    def test_team_flags_default_to_visible(self):
        """Given a new team, no role is hidden."""
        team = self.env["crm.team"].create({"name": "Fresh team"})
        self.assertFalse(
            any(
                (
                    team.hide_sdr_bdr,
                    team.hide_hunter,
                    team.hide_closer,
                    team.hide_farmer,
                )
            )
        )

    def test_form_hides_role_fields_hidden_by_team(self):
        """Given a team hiding the hunter, the form refuses edits on that field only."""
        self.team.hide_hunter = True
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Form role"
        form.team_id = self.team
        with self.assertRaises(AssertionError):
            form.hunter_id = self.hunter
        form.sdr_bdr_id = self.sdr
        form.farmer_id = self.farmer
        lead = form.save()
        self.assertEqual(lead.sdr_bdr_id, self.sdr)
        self.assertEqual(lead.farmer_id, self.farmer)
        self.assertFalse(lead.hunter_id)

    # sales order ------------------------------------------------------------------

    def _order_vals(self, **extra):
        partner = self.env["res.partner"].create({"name": "Role customer"})
        vals = {"partner_id": partner.id}
        if "fiscal_operation_id" in self.env["sale.order"]._fields:
            vals["fiscal_operation_id"] = False
        vals.update(extra)
        return vals

    def test_quotation_context_carries_roles(self):
        """Given a lead with roles, the quotation context defaults copy them."""
        lead = self.Lead.create(self._vals(self.stage_plain, **self._roles()))
        context = lead._prepare_opportunity_quotation_context()
        self.assertEqual(context["default_sdr_bdr_id"], self.sdr.id)
        self.assertEqual(context["default_hunter_id"], self.hunter.id)
        self.assertEqual(context["default_closer_id"], self.closer.id)
        self.assertEqual(context["default_farmer_id"], self.farmer.id)

    def test_quotation_context_without_roles_is_false(self):
        """Given a lead without roles, the defaults are False, not stale ids."""
        lead = self.Lead.create(self._vals(self.stage_plain))
        context = lead._prepare_opportunity_quotation_context()
        for key in (
            "default_sdr_bdr_id",
            "default_hunter_id",
            "default_closer_id",
            "default_farmer_id",
        ):
            self.assertFalse(context[key])

    def test_new_quotation_receives_roles_from_the_opportunity(self):
        """Given the quotation context, the sale order starts with the lead roles."""
        lead = self.Lead.create(self._vals(self.stage_plain, **self._roles()))
        order = (
            self.env["sale.order"]
            .with_context(**lead._prepare_opportunity_quotation_context())
            .create(self._order_vals(opportunity_id=lead.id))
        )
        self.assertEqual(order.sdr_bdr_id, self.sdr)
        self.assertEqual(order.hunter_id, self.hunter)
        self.assertEqual(order.closer_id, self.closer)
        self.assertEqual(order.farmer_id, self.farmer)

    def test_order_without_salesperson_takes_the_opportunity_owner(self):
        """Given an order without salesperson, the opportunity responsible is used."""
        lead = self.Lead.create(self._vals(self.stage_plain))
        order = self.env["sale.order"].create(
            self._order_vals(opportunity_id=lead.id, user_id=False)
        )
        self.assertEqual(order.user_id, self.owner)

    def test_order_keeps_explicit_salesperson(self):
        """Given an order with a salesperson, the opportunity owner does not override."""
        lead = self.Lead.create(self._vals(self.stage_plain))
        order = self.env["sale.order"].create(
            self._order_vals(opportunity_id=lead.id, user_id=self.farmer.id)
        )
        self.assertEqual(order.user_id, self.farmer)

    def test_order_without_opportunity_stays_unassigned(self):
        """Given an order without opportunity, no salesperson is invented."""
        order = self.env["sale.order"].create(self._order_vals(user_id=False))
        self.assertFalse(order.user_id)

    def test_batch_order_creation_applies_the_rule_to_each(self):
        """Given two orders created together, each one is handled on its own."""
        lead_a = self.Lead.create(self._vals(self.stage_plain, name="A"))
        lead_b = self.Lead.create(
            self._vals(self.stage_plain, name="B", user_id=self.hunter.id)
        )
        orders = self.env["sale.order"].create(
            [
                self._order_vals(opportunity_id=lead_a.id, user_id=False),
                self._order_vals(opportunity_id=lead_b.id, user_id=False),
            ]
        )
        self.assertEqual(orders[0].user_id, self.owner)
        self.assertEqual(orders[1].user_id, self.hunter)

    # views --------------------------------------------------------------------------

    def test_views_expose_role_fields(self):
        """Given the module views, stage, team, lead and order forms carry the roles."""
        stage = self.env["crm.stage"].get_view(self.env.ref("crm.crm_stage_form").id)
        self.assertIn("role_responsible", stage["arch"])
        team = self.env["crm.team"].get_view(
            self.env.ref("sales_team.crm_team_view_form").id
        )
        self.assertIn("hide_closer", team["arch"])
        lead = etree.fromstring(
            self.Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)["arch"]
        )
        for name in ("sdr_bdr_id", "hunter_id", "farmer_id"):
            self.assertTrue(lead.xpath("//field[@name='%s']" % name))
        order = etree.fromstring(
            self.env["sale.order"].get_view(self.env.ref("sale.view_order_form").id)[
                "arch"
            ]
        )
        for name in ("sdr_bdr_id", "hunter_id", "closer_id", "farmer_id"):
            self.assertTrue(order.xpath("//field[@name='%s']" % name))
