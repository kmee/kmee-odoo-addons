# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval

MOD = "crm_predict_revenue"


@tagged("post_install", "-at_install")
class TestCrmPredictRevenue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env["crm.lead"]
        cls.reason = cls.env["crm.lost.reason"].create({"name": "Predict reason"})

    def _lead(self, **vals):
        vals.setdefault("name", "Predict lead")
        vals.setdefault("type", "opportunity")
        return self.Lead.create(vals)

    def _stage(self, xmlid):
        return self.env.ref("%s.%s" % (MOD, xmlid))

    def _set_create_date(self, lead, days_ago):
        past = fields.Datetime.now() - timedelta(days=days_ago)
        self.env.cr.execute(
            "UPDATE crm_lead SET create_date = %s WHERE id = %s", (past, lead.id)
        )
        lead.invalidate_recordset(["create_date"])

    # weighted revenue ------------------------------------------------------

    def test_weighted_revenue_is_revenue_times_probability(self):
        """Given 1000 expected at 25 percent, the weighted revenue is 250."""
        lead = self._lead(expected_revenue=1000, probability=25)
        self.assertAlmostEqual(lead.weighted_revenue, 250.0)

    def test_weighted_revenue_follows_changes(self):
        """Given a lead, when probability or revenue change, the weight follows."""
        lead = self._lead(expected_revenue=1000, probability=50)
        self.assertAlmostEqual(lead.weighted_revenue, 500.0)
        lead.expected_revenue = 2000
        self.assertAlmostEqual(lead.weighted_revenue, 1000.0)
        lead.probability = 10
        self.assertAlmostEqual(lead.weighted_revenue, 200.0)

    def test_weighted_revenue_zero_without_probability(self):
        """Given probability zero, the weighted revenue is zero."""
        lead = self._lead(expected_revenue=1000, probability=0)
        self.assertEqual(lead.weighted_revenue, 0)

    def test_weighted_revenue_is_searchable(self):
        """Given leads of different weight, the stored field filters them."""
        big = self._lead(name="Big", expected_revenue=10000, probability=90)
        small = self._lead(name="Small", expected_revenue=100, probability=10)
        found = self.Lead.search(
            [("id", "in", (big | small).ids), ("weighted_revenue", ">", 5000)]
        )
        self.assertEqual(found, big)

    # sales cycle ---------------------------------------------------------------

    def test_won_cycle_counts_days_from_creation(self):
        """Given a lead created 10 days ago, when won, the won cycle is 10 days."""
        lead = self._lead()
        self._set_create_date(lead, 10)
        lead.action_set_won()
        self.assertEqual(lead.probability, 100)
        self.assertEqual(lead.won_sales_cycle_days, 10)
        self.assertEqual(lead.lost_sales_cycle_days, 0)

    def test_lost_cycle_counts_days_when_archived(self):
        """Given a lead created 7 days ago, when archived, the lost cycle is 7 days."""
        lead = self._lead()
        self._set_create_date(lead, 7)
        lead.action_set_lost(lost_reason_id=self.reason.id)
        self.assertFalse(lead.active)
        self.assertEqual(lead.lost_sales_cycle_days, 7)
        self.assertEqual(lead.won_sales_cycle_days, 0)

    def test_open_lead_has_no_cycle(self):
        """Given an open lead, both cycle fields are zero."""
        lead = self._lead(probability=40)
        self._set_create_date(lead, 3)
        lead.write({"name": "Still open"})
        self.assertFalse(lead.date_closed)
        self.assertEqual(lead.won_sales_cycle_days, 0)
        self.assertEqual(lead.lost_sales_cycle_days, 0)

    def test_closed_date_on_open_lead_does_not_count(self):
        """Given an active lead with 40 percent, a closing date alone is no cycle."""
        lead = self._lead(probability=40)
        self._set_create_date(lead, 3)
        lead.write({"date_closed": fields.Datetime.now()})
        self.assertEqual(lead.won_sales_cycle_days, 0)
        self.assertEqual(lead.lost_sales_cycle_days, 0)

    # activity metrics --------------------------------------------------------

    def _activity(self, lead, summary="Call"):
        return lead.activity_schedule(
            "mail.mail_activity_data_todo", summary=summary, user_id=self.env.uid
        )

    def test_outreach_count_counts_scheduled_activities(self):
        """Given a lead, each scheduled activity increases the outreach count."""
        lead = self._lead()
        self.assertEqual(lead.outreach_count, 0)
        first = self._activity(lead, "One")
        self._activity(lead, "Two")
        self.assertEqual(lead.outreach_count, 2)
        first.action_done()
        self.assertEqual(lead.outreach_count, 1)

    def test_last_activity_date_is_latest_activity_creation(self):
        """Given two activities, the last activity date is the newest creation."""
        lead = self._lead()
        self.assertFalse(lead.last_activity_date)
        old = self._activity(lead, "Old")
        new = self._activity(lead, "New")
        self.env.cr.execute(
            "UPDATE mail_activity SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=9), old.id),
        )
        (old | new).invalidate_recordset(["create_date"])
        self.env.add_to_compute(self.Lead._fields["last_activity_date"], lead)
        self.assertEqual(lead.last_activity_date, new.create_date)

    def test_days_since_last_activity(self):
        """Given the last activity created 3 days ago, the counter shows 3 days."""
        lead = self._lead()
        self.assertEqual(lead.days_since_last_activity, 0)
        activity = self._activity(lead)
        self.env.cr.execute(
            "UPDATE mail_activity SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=3, hours=1), activity.id),
        )
        activity.invalidate_recordset(["create_date"])
        self.env.add_to_compute(self.Lead._fields["last_activity_date"], lead)
        lead.invalidate_recordset(["days_since_last_activity"])
        self.assertEqual(lead.days_since_last_activity, 3)

    def test_meeting_count_counts_calendar_events(self):
        """Given a lead with two meetings, the meeting count is two."""
        lead = self._lead()
        self.assertEqual(lead.meeting_count, 0)
        for name in ("Meeting 1", "Meeting 2"):
            self.env["calendar.event"].create(
                {
                    "name": name,
                    "start": fields.Datetime.now(),
                    "stop": fields.Datetime.now() + timedelta(hours=1),
                    "opportunity_id": lead.id,
                }
            )
        lead.invalidate_recordset()
        self.assertEqual(lead.meeting_count, 2)

    def test_days_in_current_stage(self):
        """Given a stage entered 5 days ago, the days in stage is 5."""
        lead = self._lead()
        lead.date_last_stage_update = fields.Datetime.now() - timedelta(days=5)
        self.assertEqual(lead.days_in_current_stage, 5)
        lead.date_last_stage_update = fields.Datetime.now()
        self.assertEqual(lead.days_in_current_stage, 0)

    def test_source_channel_defaults_to_inbound_call(self):
        """Given a new lead, the source channel is inbound call and can be changed."""
        lead = self._lead()
        self.assertEqual(lead.source_channel, "inbound_call")
        lead.source_channel = "outbound_events"
        self.assertEqual(lead.source_channel, "outbound_events")

    # funnel data ---------------------------------------------------------------

    def test_funnel_stages_exist_in_order(self):
        """Given the module data, the funnel stages exist in pipeline order."""
        stages = [
            self._stage(x)
            for x in (
                "stage_lead_new",
                "stage_lead_qualified",
                "stage_opportunity_discovery",
                "stage_opportunity_presentation",
                "stage_opportunity_proposal",
                "stage_opportunity_negotiation",
            )
        ]
        sequences = [s.sequence for s in stages]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(len(set(sequences)), 6)

    def test_server_action_moves_opportunities_but_not_leads(self):
        """Given the proposal action, opportunities move, plain leads do not."""
        discovery = self._stage("stage_opportunity_discovery")
        opp = self._lead(name="Opp", stage_id=discovery.id)
        plain = self._lead(name="Plain", type="lead", stage_id=discovery.id)
        action = self.env.ref("%s.action_update_to_proposal" % MOD)
        action.with_context(active_model="crm.lead", active_ids=(opp | plain).ids).run()
        self.assertEqual(opp.stage_id, self._stage("stage_opportunity_proposal"))
        self.assertEqual(plain.stage_id, discovery)

    def test_each_server_action_targets_its_stage(self):
        """Given the three stage actions, each one sends the lead to its own stage."""
        for action_id, stage_id in (
            ("action_update_to_presentation", "stage_opportunity_presentation"),
            ("action_update_to_proposal", "stage_opportunity_proposal"),
            ("action_update_to_negotiation", "stage_opportunity_negotiation"),
        ):
            with self.subTest(action=action_id):
                opp = self._lead(name=action_id)
                self.env.ref("%s.%s" % (MOD, action_id)).with_context(
                    active_model="crm.lead", active_ids=opp.ids
                ).run()
                self.assertEqual(opp.stage_id, self._stage(stage_id))

    def test_automation_filters_select_leads_by_stage(self):
        """Given the filters, each one finds only the records of its stage and type."""
        mapping = {
            "filter_new_leads": ("lead", "stage_lead_new"),
            "filter_qualified_leads": ("lead", "stage_lead_qualified"),
            "filter_discovery_opportunities": (
                "opportunity",
                "stage_opportunity_discovery",
            ),
            "filter_presentation_opportunities": (
                "opportunity",
                "stage_opportunity_presentation",
            ),
            "filter_proposal_opportunities": (
                "opportunity",
                "stage_opportunity_proposal",
            ),
            "filter_negotiation_opportunities": (
                "opportunity",
                "stage_opportunity_negotiation",
            ),
        }
        for filter_id, (lead_type, stage_id) in mapping.items():
            with self.subTest(filter=filter_id):
                other_type = "lead" if lead_type == "opportunity" else "opportunity"
                inside = self._lead(
                    name="in", type=lead_type, stage_id=self._stage(stage_id).id
                )
                wrong_type = self._lead(
                    name="type", type=other_type, stage_id=self._stage(stage_id).id
                )
                wrong_stage = self._lead(
                    name="stage",
                    type=lead_type,
                    stage_id=self.env.ref("crm.stage_lead1").id,
                )
                record = self.env.ref("%s.%s" % (MOD, filter_id))
                domain = safe_eval(record.domain, {"ref": self.env.ref})
                found = self.Lead.search(
                    domain + [("id", "in", (inside | wrong_type | wrong_stage).ids)]
                )
                self.assertEqual(found, inside)

    def test_discovery_automation_schedules_the_discovery_meeting(self):
        """Given an opportunity in discovery, running the automation schedules the meeting."""
        config = self.env.ref("%s.automation_discovery_phase" % MOD)
        self.assertEqual(config.state, "periodic")
        opp = self._lead(
            name="Discovery opp",
            stage_id=self._stage("stage_opportunity_discovery").id,
        )
        outside = self._lead(
            name="Outside",
            stage_id=self._stage("stage_opportunity_negotiation").id,
        )
        config.run_automation()
        self.env["automation.record.step"]._cron_automation_steps()
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "crm.lead"),
                ("res_id", "in", (opp | outside).ids),
                ("summary", "=", "Reunião de Descoberta"),
            ]
        )
        self.assertEqual(activities.mapped("res_id"), opp.ids)
        self.assertEqual(activities.user_id, self.env.ref("base.user_admin"))

    def test_automation_steps_form_the_expected_chain(self):
        """Given the discovery automation, its steps chain start, done, then action."""
        schedule = self.env.ref("%s.automation_step_schedule_discovery" % MOD)
        materials = self.env.ref("%s.automation_step_send_materials" % MOD)
        update = self.env.ref("%s.automation_step_update_to_presentation" % MOD)
        self.assertEqual(schedule.trigger_type, "start")
        self.assertEqual(materials.parent_id, schedule)
        self.assertEqual(materials.trigger_type, "activity_done")
        self.assertEqual(update.parent_id, materials)
        self.assertEqual(
            update.server_action_id,
            self.env.ref("%s.action_update_to_presentation" % MOD),
        )
        presentation = self.env.ref("%s.automation_presentation_phase" % MOD)
        quote = self.env.ref("%s.automation_step_create_proposal_activity" % MOD)
        self.assertEqual(quote.configuration_id, presentation)
        self.assertEqual(
            quote.activity_type_id,
            self.env.ref("%s.mail_activity_demo_make_quote" % MOD),
        )

    def test_mail_templates_render_for_a_lead(self):
        """Given the module mail templates, each renders subject and body for a lead."""
        lead = self._lead(
            name="Render lead", contact_name="Rita", email_from="rita@example.com"
        )
        for xmlid in (
            "mail_template_discovery_followup",
            "mail_template_initial_contact",
            "mail_template_followup",
            "mail_template_notify_ae",
        ):
            with self.subTest(template=xmlid):
                template = self.env.ref("%s.%s" % (MOD, xmlid))
                self.assertEqual(template.model, "crm.lead")
                subject = template._render_field("subject", lead.ids)[lead.id]
                body = template._render_field("body_html", lead.ids)[lead.id]
                self.assertTrue(subject)
                self.assertNotIn("{{", subject)
                self.assertTrue(body)

    def test_notify_ae_template_shows_bant_only_when_available(self):
        """Given the AE notice, BANT data appears only if the BANT fields exist."""
        lead = self._lead(name="AE notice")
        template = self.env.ref("%s.mail_template_notify_ae" % MOD)
        body = str(template._render_field("body_html", lead.ids)[lead.id])
        self.assertIn("AE notice", body)
        if "bant_budget_amount" in self.Lead._fields:
            self.assertIn("Qualificação BANT", body)
        else:
            self.assertNotIn("Qualificação BANT", body)

    def test_discovery_template_greets_the_contact(self):
        """Given a contact name, the discovery template greets that person."""
        lead = self._lead(name="Greet", contact_name="Rita")
        template = self.env.ref("%s.mail_template_discovery_followup" % MOD)
        body = template._render_field("body_html", lead.ids)[lead.id]
        self.assertIn("Rita", str(body))

    def test_teams_are_configured_for_each_funnel_role(self):
        """Given the module teams, SDRs handle leads and executives opportunities."""
        outbound = self.env.ref("%s.team_sdr_outbound" % MOD)
        inbound = self.env.ref("%s.team_sdr_inbound" % MOD)
        executives = self.env.ref("%s.team_account_executives" % MOD)
        self.assertTrue(outbound.use_leads and not outbound.use_opportunities)
        self.assertTrue(inbound.use_leads and inbound.use_opportunities)
        self.assertTrue(executives.use_opportunities and not executives.use_leads)
        self.assertEqual(outbound.alias_name, "leads")
        self.assertEqual(inbound.alias_name, "qualificar")
        self.assertEqual(executives.alias_name, "oportunidades")
        self.assertEqual(executives.assignment_domain, "[('type', '=', 'opportunity')]")

    def test_bant_tags_and_activity_types_exist(self):
        """Given the module data, BANT tags and handoff activity types are available."""
        for xmlid in (
            "tag_budget_defined",
            "tag_authority_decision_maker",
            "tag_need_identified",
            "tag_timeline_urgent",
        ):
            self.assertTrue(self.env.ref("%s.%s" % (MOD, xmlid)).name)
        for xmlid in (
            "activity_type_qualification_call",
            "activity_type_handoff_meeting",
            "activity_type_bant_assessment",
        ):
            activity_type = self.env.ref("%s.%s" % (MOD, xmlid))
            self.assertEqual(activity_type.res_model, "crm.lead")
        call = self.env.ref("%s.activity_type_qualification_call" % MOD)
        self.assertEqual(call.category, "phonecall")

    # views ---------------------------------------------------------------------

    def test_form_has_analytics_page_with_moved_groups(self):
        """Given the lead form, the Analytics page holds the metrics and moved groups."""
        arch = etree.fromstring(
            self.Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)["arch"]
        )
        page = arch.xpath("//page[@name='predictive_analysis']")
        self.assertEqual(len(page), 1)
        names = set(page[0].xpath(".//field/@name"))
        self.assertTrue(
            {
                "weighted_revenue",
                "outreach_count",
                "meeting_count",
                "last_activity_date",
                "days_since_last_activity",
                "days_in_current_stage",
                "campaign_id",
            }
            <= names
        )
        self.assertFalse(arch.xpath("//page[@name='lead']//field[@name='campaign_id']"))
        self.assertTrue(arch.xpath("//field[@name='source_channel']"))
        self.assertTrue(arch.xpath("//field[@name='won_sales_cycle_days']"))

    def test_prediction_report_action_and_menu(self):
        """Given the report action, it lists opportunities in pivot and graph."""
        action = self.env.ref("%s.action_crm_revenue_prediction_report" % MOD)
        menu = self.env.ref("%s.menu_crm_revenue_prediction" % MOD)
        self.assertEqual(menu.action, action)
        self.assertEqual(action.view_mode, "pivot,graph")
        opp = self._lead(expected_revenue=500, probability=20)
        plain = self._lead(name="Plain", type="lead")
        found = self.Lead.search(safe_eval(action.domain))
        self.assertIn(opp, found)
        self.assertNotIn(plain, found)
        groups = self.Lead.read_group(
            [("id", "=", opp.id)], ["weighted_revenue:sum"], ["team_id"]
        )
        self.assertAlmostEqual(groups[0]["weighted_revenue"], 100.0)
