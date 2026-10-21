# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmWip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        Stage = cls.env["crm.stage"]
        cls.stage_new = Stage.create({"name": "WIP new", "state": "draft"})
        cls.stage_open = Stage.create({"name": "WIP open", "state": "open"})
        cls.stage_pending = Stage.create({"name": "WIP pending", "state": "pending"})
        cls.stage_done = Stage.create({"name": "WIP won", "state": "done"})
        cls.stage_none = Stage.create({"name": "WIP no state"})
        cls.Lead = cls.env["crm.lead"]

    def _lead(self, stage, name="WIP lead"):
        return self.Lead.create(
            {"name": name, "type": "opportunity", "stage_id": stage.id}
        )

    def _wips(self, lead):
        return self.env["base.wip"].search(
            [("model_id.model", "=", "crm.lead"), ("res_id", "=", lead.id)],
            order="id",
        )

    # stage / lead state -------------------------------------------------

    def test_stage_state_labels(self):
        """Given the stage state field, then done reads Won and cancelled Lost."""
        labels = dict(
            self.env["crm.stage"]._fields["state"]._description_selection(self.env)
        )
        self.assertEqual(labels["done"], "Won")
        self.assertEqual(labels["cancelled"], "Lost")
        self.assertEqual(labels["open"], "In Progress")

    def test_lead_state_follows_stage_on_create(self):
        """Given a stage in progress, when a lead is created in it, state is open."""
        lead = self._lead(self.stage_open)
        self.assertEqual(lead.state, "open")

    def test_lead_state_follows_stage_changes(self):
        """Given a lead, when its stage changes or the stage state changes, it follows."""
        lead = self._lead(self.stage_open)
        lead.stage_id = self.stage_pending
        self.assertEqual(lead.state, "pending")
        self.stage_pending.state = "done"
        self.assertEqual(lead.state, "done")

    def test_lead_state_is_stored_and_searchable(self):
        """Given leads in different stages, searching by state filters them."""
        won = self._lead(self.stage_done)
        working = self._lead(self.stage_open)
        found = self.Lead.search(
            [("id", "in", (won | working).ids), ("state", "=", "done")]
        )
        self.assertEqual(found, won)

    # wip history --------------------------------------------------------

    def test_create_opens_running_wip_with_lead_state(self):
        """Given a stage in progress, a new lead gets one running wip in that state."""
        lead = self._lead(self.stage_open)
        wips = self._wips(lead)
        self.assertEqual(len(wips), 1)
        self.assertEqual(wips.state, "open")
        self.assertEqual(wips.wip_state, "running")
        self.assertEqual(lead.wip_ids, wips)

    def test_create_in_stage_without_state_opens_draft_wip(self):
        """Given a stage with no state, a new lead starts a draft wip."""
        lead = self._lead(self.stage_none)
        self.assertFalse(lead.state)
        self.assertEqual(self._wips(lead).state, "draft")

    def test_create_in_done_stage_opens_no_wip(self):
        """Given a won stage, a new lead has no work in progress."""
        lead = self._lead(self.stage_done)
        self.assertFalse(self._wips(lead))

    def test_stage_change_closes_previous_and_opens_new_wip(self):
        """Given a lead in progress, when it moves to pending, history keeps both."""
        lead = self._lead(self.stage_open)
        first = self._wips(lead)
        lead.write({"stage_id": self.stage_pending.id})
        wips = self._wips(lead)
        self.assertEqual(len(wips), 2)
        self.assertEqual(first.wip_state, "closed")
        self.assertTrue(first.date_hour_stop)
        new = wips - first
        self.assertEqual(new.state, "pending")
        self.assertEqual(new.wip_state, "running")

    def test_moving_to_done_closes_wip_without_opening_another(self):
        """Given a lead in progress, when it is won, the wip closes and none opens."""
        lead = self._lead(self.stage_open)
        lead.write({"stage_id": self.stage_done.id})
        wips = self._wips(lead)
        self.assertEqual(len(wips), 1)
        self.assertEqual(wips.wip_state, "closed")

    def test_write_without_state_change_keeps_wip(self):
        """Given a lead in progress, when only its name changes, the wip is untouched."""
        lead = self._lead(self.stage_open)
        before = self._wips(lead)
        lead.write({"name": "Renamed"})
        self.assertEqual(self._wips(lead), before)
        self.assertEqual(before.wip_state, "running")

    def test_batch_create_gives_each_lead_its_wip(self):
        """Given two leads created at once, each has exactly its own wip."""
        leads = self.Lead.create(
            [
                {"name": "A", "type": "opportunity", "stage_id": self.stage_open.id},
                {"name": "B", "type": "opportunity", "stage_id": self.stage_pending.id},
            ]
        )
        self.assertEqual(self._wips(leads[0]).state, "open")
        self.assertEqual(self._wips(leads[1]).state, "pending")
        self.assertEqual(len(self._wips(leads[0])), 1)
        self.assertEqual(len(self._wips(leads[1])), 1)

    def test_batch_write_moves_every_lead(self):
        """Given two leads, when both move to a stage at once, both get new wips."""
        leads = self._lead(self.stage_open, "A") | self._lead(self.stage_open, "B")
        leads.write({"stage_id": self.stage_pending.id})
        for lead in leads:
            wips = self._wips(lead)
            self.assertEqual(wips.mapped("state"), ["open", "pending"])
            self.assertEqual(wips.mapped("wip_state"), ["closed", "running"])

    def test_set_won_on_several_leads(self):
        """Given several open leads, marking them won in one call closes their wips."""
        leads = self._lead(self.stage_open, "A") | self._lead(self.stage_open, "B")
        won_stage = self.env["crm.stage"].search([("is_won", "=", True)], limit=1)
        won_stage.state = "done"
        leads.action_set_won()
        for lead in leads:
            self.assertEqual(lead.state, "done")
            self.assertEqual(set(self._wips(lead).mapped("wip_state")), {"closed"})

    def test_salesman_creates_and_moves_lead(self):
        """Given a salesman without settings rights, the wip history still works."""
        salesman = self.env["res.users"].create(
            {
                "name": "WIP salesman",
                "login": "wip_salesman",
                "group_ids": [
                    (6, 0, self.env.ref("sales_team.group_sale_salesman").ids)
                ],
            }
        )
        lead = self.Lead.with_user(salesman).create(
            {
                "name": "Salesman lead",
                "type": "opportunity",
                "stage_id": self.stage_open.id,
            }
        )
        lead.write({"stage_id": self.stage_pending.id})
        self.assertEqual(lead.wip_ids.mapped("state"), ["open", "pending"])
        self.assertEqual(lead.wip_ids.mapped("user_id"), salesman)

    # metrics ------------------------------------------------------------

    def test_metrics_reflect_wip_history(self):
        """Given a lead 10 min new then 20 min in progress, metrics add up."""
        lead = self._lead(self.stage_new)
        now = fields.Datetime.now()
        draft = self._wips(lead)
        draft.write(
            {
                "date_hour_start": now - timedelta(minutes=30),
                "date_hour_stop": now - timedelta(minutes=20),
                "wip_state": "closed",
            }
        )
        lead.stage_id = self.stage_open
        running = self._wips(lead) - draft
        running.date_hour_start = now - timedelta(minutes=20)
        lead.invalidate_recordset()
        self.assertAlmostEqual(lead.reaction_time_float, 600, delta=2)
        self.assertGreaterEqual(lead.logged_time_float, 1199)
        self.assertGreaterEqual(lead.cycle_time_float, 1199)
        self.assertGreaterEqual(lead.lead_time_float, 1799)
        self.assertAlmostEqual(lead.flow_efficience, 2 / 3, places=2)
        self.assertEqual(lead.reaction_time, "10 min")
        self.assertTrue(lead.lead_time.startswith("30 min"))

    # views ----------------------------------------------------------------

    def test_views_expose_wip_fields(self):
        """Given the module views, stage form and lead form show the wip fields."""
        stage_view = self.env["crm.stage"].get_view(
            self.env.ref("crm.crm_stage_form").id
        )
        self.assertIn('name="state"', stage_view["arch"])
        lead_view = self.Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)
        self.assertIn('name="wip_ids"', lead_view["arch"])
        self.assertIn('name="flow_efficience"', lead_view["arch"])
