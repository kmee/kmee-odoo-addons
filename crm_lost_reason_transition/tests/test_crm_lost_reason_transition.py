# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestCrmLostReasonTransition(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env["crm.lead"]
        cls.Transition = cls.env["crm.lost.reason.transition"]
        cls.team_src = cls.env["crm.team"].create({"name": "Source team"})
        cls.team_rec = cls.env["crm.team"].create({"name": "Recovery team"})
        cls.team_rec2 = cls.env["crm.team"].create({"name": "Recovery team 2"})
        Stage = cls.env["crm.stage"]
        cls.stage_new = Stage.create({"name": "LRT new"})
        cls.stage_rec = Stage.create({"name": "LRT recovery"})
        cls.stage_rec2 = Stage.create({"name": "LRT recovery 2"})
        Reason = cls.env["crm.lost.reason"]
        cls.reason_price = Reason.create({"name": "Too expensive"})
        cls.reason_comp = Reason.create({"name": "Chose competitor"})
        cls.reason_free = Reason.create({"name": "No transition"})
        cls.t_price = cls.Transition.create(
            {
                "lost_reason_id": cls.reason_price.id,
                "team_id": cls.team_rec.id,
                "target_stage_id": cls.stage_rec.id,
            }
        )
        cls.t_comp = cls.Transition.create(
            {
                "lost_reason_id": cls.reason_comp.id,
                "team_id": cls.team_rec2.id,
                "target_stage_id": cls.stage_rec2.id,
            }
        )

    def _lead(self, name="LRT lead"):
        return self.Lead.create(
            {
                "name": name,
                "type": "opportunity",
                "team_id": self.team_src.id,
                "stage_id": self.stage_new.id,
            }
        )

    # configuration model -----------------------------------------------------

    def test_name_is_built_from_reason_team_and_stage(self):
        """Given a transition, its name shows reason | team / stage."""
        self.assertEqual(
            self.t_price.name, "Too expensive | Recovery team / LRT recovery"
        )

    def test_name_follows_renames_of_related_records(self):
        """Given a transition, when the team or reason is renamed, the name follows."""
        self.team_rec.name = "Win-back team"
        self.reason_price.name = "Price too high"
        self.assertEqual(
            self.t_price.name, "Price too high | Win-back team / LRT recovery"
        )

    def test_same_reason_and_stage_cannot_repeat(self):
        """Given a configured reason and stage, repeating the pair is rejected."""
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.Transition.create(
                    {
                        "lost_reason_id": self.reason_price.id,
                        "team_id": self.team_rec2.id,
                        "target_stage_id": self.stage_rec.id,
                    }
                )

    def test_same_reason_with_another_stage_is_allowed(self):
        """Given a configured reason, a different target stage is a new transition."""
        extra = self.Transition.create(
            {
                "lost_reason_id": self.reason_price.id,
                "team_id": self.team_rec.id,
                "target_stage_id": self.stage_rec2.id,
            }
        )
        self.assertTrue(extra)

    def test_required_fields(self):
        """Given a transition without target stage, creation fails."""
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.Transition.create(
                    {
                        "lost_reason_id": self.reason_free.id,
                        "team_id": self.team_rec.id,
                    }
                )

    def test_config_form_creates_transition(self):
        """Given the config form, filling it saves a transition with the generated name."""
        form = Form(self.Transition)
        form.lost_reason_id = self.reason_free
        form.team_id = self.team_rec
        form.target_stage_id = self.stage_rec
        record = form.save()
        self.assertEqual(record.name, "No transition | Recovery team / LRT recovery")

    # applying the transition ---------------------------------------------------

    def test_lost_lead_goes_to_configured_team_and_stage(self):
        """Given a lead, when lost for a configured reason, it is reopened elsewhere."""
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.reason_price.id)
        self.assertTrue(lead.active)
        self.assertEqual(lead.team_id, self.team_rec)
        self.assertEqual(lead.stage_id, self.stage_rec)
        self.assertEqual(lead.lost_reason_id, self.reason_price)

    def test_lost_lead_without_transition_stays_archived(self):
        """Given a reason without transition, the lead is simply lost."""
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.reason_free.id)
        self.assertFalse(lead.active)
        self.assertEqual(lead.team_id, self.team_src)
        self.assertEqual(lead.stage_id, self.stage_new)

    def test_lost_without_reason_is_refused(self):
        """Given no reason, marking as lost raises and leaves the lead untouched."""
        lead = self._lead()
        with self.assertRaises(UserError) as error:
            lead.action_set_lost()
        self.assertIn("select a lost reason", str(error.exception))
        lead.invalidate_recordset()
        self.assertTrue(lead.active)
        self.assertEqual(lead.stage_id, self.stage_new)

    def test_wizard_flow_applies_transition(self):
        """Given the lost wizard, applying a reason moves each selected lead."""
        leads = self._lead("W1") | self._lead("W2")
        wizard = self.env["crm.lead.lost"].create(
            {"lead_ids": [(6, 0, leads.ids)], "lost_reason_id": self.reason_comp.id}
        )
        wizard.action_lost_reason_apply()
        for lead in leads:
            self.assertTrue(lead.active)
            self.assertEqual(lead.team_id, self.team_rec2)
            self.assertEqual(lead.stage_id, self.stage_rec2)

    def test_batch_with_different_reasons_is_handled_per_lead(self):
        """Given leads lost one by one with different reasons, each follows its rule."""
        first = self._lead("P")
        second = self._lead("C")
        first.action_set_lost(lost_reason_id=self.reason_price.id)
        second.action_set_lost(lost_reason_id=self.reason_comp.id)
        self.assertEqual(first.stage_id, self.stage_rec)
        self.assertEqual(second.stage_id, self.stage_rec2)

    def test_writing_reason_on_archived_lead_applies_transition(self):
        """Given an archived lead, when a reason is written, the transition applies."""
        lead = self._lead()
        lead.action_archive()
        lead.write({"lost_reason_id": self.reason_price.id})
        self.assertTrue(lead.active)
        self.assertEqual(lead.stage_id, self.stage_rec)
        self.assertEqual(lead.team_id, self.team_rec)

    def test_writing_reason_on_active_lead_does_nothing(self):
        """Given an active lead, writing a reason does not move it."""
        lead = self._lead()
        lead.write({"lost_reason_id": self.reason_price.id})
        self.assertEqual(lead.stage_id, self.stage_new)
        self.assertEqual(lead.team_id, self.team_src)

    def test_first_configured_transition_wins_for_a_reason(self):
        """Given two transitions for a reason, the oldest one is used."""
        self.Transition.create(
            {
                "lost_reason_id": self.reason_price.id,
                "team_id": self.team_rec2.id,
                "target_stage_id": self.stage_rec2.id,
            }
        )
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.reason_price.id)
        self.assertEqual(lead.stage_id, self.stage_rec)

    def test_apply_transition_skips_leads_without_reason_but_continues(self):
        """Given leads with and without reason, the ones with a reason still move."""
        no_reason = self._lead("none")
        with_reason = self._lead("with")
        with_reason.lost_reason_id = self.reason_price
        (no_reason | with_reason)._apply_lost_reason_transition()
        self.assertEqual(no_reason.stage_id, self.stage_new)
        self.assertEqual(with_reason.stage_id, self.stage_rec)

    # access / menus -------------------------------------------------------------

    def _user(self, login, group_xmlid):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_salesman_reads_but_cannot_edit_transitions(self):
        """Given a salesman, he can read transitions but not create or change them."""
        salesman = self._user("lrt_sales", "sales_team.group_sale_salesman")
        transition = self.t_price.with_user(salesman)
        self.assertEqual(transition.lost_reason_id, self.reason_price)
        with self.assertRaises(AccessError):
            transition.write({"team_id": self.team_rec2.id})
        with self.assertRaises(AccessError):
            self.Transition.with_user(salesman).create(
                {
                    "lost_reason_id": self.reason_free.id,
                    "team_id": self.team_rec.id,
                    "target_stage_id": self.stage_rec.id,
                }
            )

    def test_salesman_marks_lead_lost_and_transition_applies(self):
        """Given a salesman, losing a lead still redirects it (ACL read is enough)."""
        salesman = self._user("lrt_sales2", "sales_team.group_sale_salesman")
        lead = self._lead()
        lead.user_id = salesman
        lead.with_user(salesman).action_set_lost(lost_reason_id=self.reason_price.id)
        self.assertTrue(lead.active)
        self.assertEqual(lead.stage_id, self.stage_rec)

    def test_manager_manages_transitions(self):
        """Given a sales manager, creating and deleting transitions is allowed."""
        manager = self._user("lrt_mgr", "sales_team.group_sale_manager")
        record = self.Transition.with_user(manager).create(
            {
                "lost_reason_id": self.reason_free.id,
                "team_id": self.team_rec.id,
                "target_stage_id": self.stage_rec.id,
            }
        )
        record.unlink()
        self.assertFalse(record.exists())

    def test_menu_and_action_are_wired(self):
        """Given the module, the config menu opens the transition list and form."""
        menu = self.env.ref(
            "crm_lost_reason_transition.menu_crm_lost_reason_transition"
        )
        action = self.env.ref(
            "crm_lost_reason_transition.action_crm_lost_reason_transition"
        )
        self.assertEqual(menu.action, action)
        self.assertEqual(menu.parent_id, self.env.ref("crm.menu_crm_config_lead"))
        self.assertEqual(action.res_model, "crm.lost.reason.transition")
        self.assertEqual(action.view_mode, "list,form")
        for mode in ("list", "form"):
            arch = self.Transition.get_view(view_type=mode)["arch"]
            self.assertIn("target_stage_id", arch)
