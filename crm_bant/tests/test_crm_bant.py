# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form, TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestCrmBant(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lead = cls.env["crm.lead"].with_context(tracking_disable=True)
        cls.team = cls.env["crm.team"].create({"name": "BANT team"})

    def _lead(self, **vals):
        vals.setdefault("name", "BANT lead")
        vals.setdefault("type", "opportunity")
        return self.Lead.create(vals)

    # defaults ---------------------------------------------------------

    def test_new_lead_is_unqualified_and_undefined(self):
        """Given a new lead, then every BANT dimension is undefined and score 0."""
        lead = self._lead()
        self.assertEqual(lead.bant_budget_status, "undefined")
        self.assertEqual(lead.bant_authority_status, "undefined")
        self.assertEqual(lead.bant_need_status, "undefined")
        self.assertEqual(lead.bant_timeline_status, "undefined")
        self.assertEqual(lead.bant_total_score, 0)
        self.assertEqual(lead.bant_qualification_status, "unqualified")
        self.assertEqual(lead.bant_progress, 0)

    # dimension scores -------------------------------------------------

    def _assert_dimension(self, field, score_field, table):
        for status, expected in table.items():
            with self.subTest(status=status):
                lead = self._lead(**{field: status})
                self.assertEqual(lead[score_field], expected)

    def test_budget_score_by_status(self):
        """Given a budget status, then the budget score is 0/0/2/3."""
        self._assert_dimension(
            "bant_budget_status",
            "bant_budget_score",
            {"undefined": 0, "no_budget": 0, "budget_defined": 2, "budget_approved": 3},
        )

    def test_authority_score_by_status(self):
        """Given an authority status, then the score ranks it from 0 to 3."""
        self._assert_dimension(
            "bant_authority_status",
            "bant_authority_score",
            {
                "undefined": 0,
                "influencer": 1,
                "recommender": 2,
                "decision_maker": 3,
                "approver": 3,
            },
        )

    def test_need_score_by_status(self):
        """Given a need status, then the score ranks it from 0 to 3."""
        self._assert_dimension(
            "bant_need_status",
            "bant_need_score",
            {
                "undefined": 0,
                "nice_to_have": 1,
                "important": 2,
                "critical": 3,
                "strategic": 3,
            },
        )

    def test_timeline_score_by_status(self):
        """Given a timeline status, then nearer deadlines score higher."""
        self._assert_dimension(
            "bant_timeline_status",
            "bant_timeline_score",
            {
                "undefined": 0,
                "no_timeline": 0,
                "long_term": 1,
                "medium_term": 2,
                "short_term": 3,
                "immediate": 3,
            },
        )

    # total / qualification ---------------------------------------------

    def _full(self, budget, authority, need, timeline):
        return self._lead(
            bant_budget_status=budget,
            bant_authority_status=authority,
            bant_need_status=need,
            bant_timeline_status=timeline,
        )

    def test_total_score_is_sum_of_dimensions(self):
        """Given 2+1+3+2 points, the total score is 8."""
        lead = self._full("budget_defined", "influencer", "critical", "medium_term")
        self.assertEqual(lead.bant_total_score, 8)

    def test_qualification_partial_below_six(self):
        """Given a total of 3, the lead is partially qualified."""
        lead = self._lead(bant_budget_status="budget_approved")
        self.assertEqual(lead.bant_total_score, 3)
        self.assertEqual(lead.bant_qualification_status, "partially_qualified")

    def test_qualification_boundary_at_six_is_qualified(self):
        """Given a total of exactly 6, the lead is qualified."""
        lead = self._lead(
            bant_budget_status="budget_approved",
            bant_authority_status="approver",
        )
        self.assertEqual(lead.bant_total_score, 6)
        self.assertEqual(lead.bant_qualification_status, "qualified")

    def test_qualification_nine_with_a_missing_dimension_is_qualified(self):
        """Given 9 points and a dimension at zero, the lead is only qualified."""
        lead = self._full("budget_approved", "approver", "strategic", "undefined")
        self.assertEqual(lead.bant_total_score, 9)
        self.assertEqual(lead.bant_qualification_status, "qualified")

    def test_qualification_fully_when_ten_or_more_in_all_dimensions(self):
        """Given 10 points across all dimensions, the lead is fully qualified."""
        lead = self._full("budget_approved", "approver", "strategic", "long_term")
        self.assertEqual(lead.bant_total_score, 10)
        self.assertEqual(lead.bant_qualification_status, "fully_qualified")

    def test_scores_recomputed_when_status_changes(self):
        """Given a qualified lead, when a status regresses, the scores follow."""
        lead = self._full("budget_approved", "approver", "strategic", "immediate")
        self.assertEqual(lead.bant_qualification_status, "fully_qualified")
        lead.write({"bant_budget_status": "no_budget"})
        self.assertEqual(lead.bant_budget_score, 0)
        self.assertEqual(lead.bant_total_score, 9)
        self.assertEqual(lead.bant_qualification_status, "qualified")

    def test_progress_is_percentage_of_maximum(self):
        """Given 6 of 12 points, the progress is 50 percent."""
        lead = self._lead(
            bant_budget_status="budget_approved", bant_authority_status="approver"
        )
        self.assertEqual(lead.bant_progress, 50)
        lead.write(
            {"bant_need_status": "strategic", "bant_timeline_status": "immediate"}
        )
        self.assertEqual(lead.bant_progress, 100)

    def test_progress_follows_score_in_same_transaction(self):
        """Given a read progress, when a status is written, progress is refreshed."""
        lead = self._lead()
        self.assertEqual(lead.bant_progress, 0)
        lead.write({"bant_budget_status": "budget_approved"})
        self.assertEqual(lead.bant_progress, 25)

    # stored / searchable -----------------------------------------------

    def test_qualification_is_searchable_and_groupable(self):
        """Given leads of different quality, search and read_group split them."""
        weak = self._lead(team_id=self.team.id)
        strong = self._full("budget_approved", "approver", "strategic", "immediate")
        strong.team_id = self.team
        domain = [("id", "in", (weak | strong).ids)]
        found = self.Lead.search(
            domain + [("bant_qualification_status", "=", "fully_qualified")]
        )
        self.assertEqual(found, strong)
        groups = self.Lead._read_group(
            domain, ["bant_qualification_status"], ["__count", "bant_total_score:sum"]
        )
        by_status = {status: count for status, count, _score in groups}
        self.assertEqual(by_status, {"unqualified": 1, "fully_qualified": 1})

    # tracking ----------------------------------------------------------

    def test_status_changes_are_tracked_in_chatter(self):
        """Given a lead, when the budget status changes, chatter tracks it."""
        lead = self.env["crm.lead"].create({"name": "Tracked", "type": "opportunity"})
        self.env.cr.precommit.run()  # records created in this transaction are not tracked
        lead.write({"bant_budget_status": "budget_defined"})
        self.env.cr.precommit.run()  # tracking is finalized before commit
        # 20.0 renders the tracked change in the message body (mail.tracking.value
        # moved to the optional mail_tracking module)
        messages = self.env["mail.message"].search(
            [("model", "=", "crm.lead"), ("res_id", "=", lead.id)]
        )
        tracked = messages.filtered(lambda m: "Budget Defined" in (m.body or ""))
        self.assertEqual(len(tracked), 1)
        self.assertIn("Undefined", tracked.body)

    # form view behaviour -------------------------------------------------

    def test_form_updates_scores_live(self):
        """Given the form, when statuses are picked, scores update through onchange."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Live BANT"
        form.bant_budget_status = "budget_approved"
        form.bant_authority_status = "approver"
        self.assertEqual(form.bant_total_score, 6)
        self.assertEqual(form.bant_progress, 50)
        lead = form.save()
        self.assertEqual(lead.bant_qualification_status, "qualified")

    def test_form_hides_budget_details_until_budget_is_defined(self):
        """Given an undefined budget, the amount is hidden; defined, it is editable."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Budget form"
        with self.assertRaises(AssertionError):
            form.bant_budget_amount = 1000
        form.bant_budget_status = "budget_defined"
        form.bant_budget_amount = 1000
        form.bant_budget_timeframe = "next_quarter"
        lead = form.save()
        self.assertEqual(lead.bant_budget_amount, 1000)
        self.assertEqual(lead.bant_budget_timeframe, "next_quarter")

    def test_form_hides_authority_details_when_undefined(self):
        """Given an undefined authority, the contact is hidden until it is set."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Authority form"
        with self.assertRaises(AssertionError):
            form.bant_authority_contact = "Ana"
        form.bant_authority_status = "decision_maker"
        form.bant_authority_contact = "Ana"
        form.bant_authority_role = "CFO"
        lead = form.save()
        self.assertEqual(lead.bant_authority_contact, "Ana")

    def test_form_hides_timeline_details_without_timeline(self):
        """Given 'no timeline', the target date stays hidden."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Timeline form"
        form.bant_timeline_status = "no_timeline"
        with self.assertRaises(AssertionError):
            form.bant_timeline_date = "2027-01-01"
        form.bant_timeline_status = "short_term"
        form.bant_timeline_date = "2027-01-01"
        lead = form.save()
        self.assertEqual(str(lead.bant_timeline_date), "2027-01-01")

    def test_form_hides_need_details_when_undefined(self):
        """Given an undefined need, the description is hidden until it is set."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Need form"
        with self.assertRaises(AssertionError):
            form.bant_need_description = "Pain"
        form.bant_need_status = "important"
        form.bant_need_description = "Pain"
        lead = form.save()
        self.assertEqual(lead.bant_need_description, "Pain")

    # views / dashboard ---------------------------------------------------

    def test_views_are_extended(self):
        """Given the module, form, list, kanban and search views carry BANT."""
        Lead = self.env["crm.lead"]
        form = Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)["arch"]
        self.assertIn("bant_total_score", form)
        self.assertIn("bant_qualification_status", form)
        tree = Lead.get_view(self.env.ref("crm.crm_case_tree_view_oppor").id)["arch"]
        self.assertIn("bant_qualification_status", tree)
        kanban = Lead.get_view(self.env.ref("crm.crm_case_kanban_view_leads").id)[
            "arch"
        ]
        self.assertIn("bant_qualification_status", kanban)
        search = Lead.get_view(
            self.env.ref("crm.view_crm_case_opportunities_filter").id
        )["arch"]
        names = etree.fromstring(search).xpath("//filter/@name")
        self.assertIn("bant_qualified", names)
        self.assertIn("groupby_timeline_status", names)

    def test_search_filters_split_qualified_from_unqualified(self):
        """Given the module filters, qualified/unqualified domains pick the right leads."""
        weak = self._lead(bant_budget_status="budget_approved")
        mid = self._full("budget_approved", "approver", "undefined", "undefined")
        ids = [("id", "in", (weak | mid).ids)]
        search = self.env["crm.lead"].get_view(
            self.env.ref("crm.view_crm_case_opportunities_filter").id
        )["arch"]
        doc = etree.fromstring(search)
        qualified = safe_eval(doc.xpath("//filter[@name='bant_qualified']/@domain")[0])
        unqualified = safe_eval(
            doc.xpath("//filter[@name='bant_unqualified']/@domain")[0]
        )
        self.assertEqual(self.Lead.search(ids + qualified), mid)
        self.assertEqual(self.Lead.search(ids + unqualified), weak)

    def test_dashboard_action_lists_only_opportunities(self):
        """Given the BANT dashboard action, only opportunities are in its domain."""
        action = self.env.ref("crm_bant.action_bant_dashboard")
        self.assertEqual(action.view_mode, "graph,pivot")
        lead = self._lead(name="Opp")
        plain = self._lead(name="Plain lead", type="lead")
        found = self.Lead.search(safe_eval(action.domain))
        self.assertIn(lead, found)
        self.assertNotIn(plain, found)
        self.assertEqual(
            action.view_ids.sorted("sequence").mapped("view_mode"), ["graph", "pivot"]
        )

    def test_dashboard_pivot_and_graph_group_by_qualification(self):
        """Given the dashboard views, grouping by team and status gives counts."""
        self._lead(team_id=self.team.id)
        self._full(
            "budget_approved", "approver", "strategic", "immediate"
        ).team_id = self.team
        for view in ("bant_qualification_graph", "bant_qualification_pivot"):
            arch = self.env["crm.lead"].get_view(self.env.ref("crm_bant.%s" % view).id)
            self.assertIn("bant_qualification_status", arch["arch"])
        groups = self.Lead._read_group(
            [("team_id", "=", self.team.id)],
            ["team_id", "bant_qualification_status"],
            ["__count", "expected_revenue:sum", "bant_total_score:sum"],
        )
        counts = {status: count for _team, status, count, _rev, _score in groups}
        self.assertEqual(counts, {"unqualified": 1, "fully_qualified": 1})
        self.assertTrue(self.env.ref("crm_bant.menu_bant_dashboard").action)

    # module metadata --------------------------------------------------

    def test_module_metadata_matches_the_module(self):
        """Given the installed module, then it is AGPL-3 like the repository,
        depends only on crm and its description talks about BANT."""
        module = self.env["ir.module.module"].search([("name", "=", "crm_bant")])
        self.assertEqual(module.license, "AGPL-3")
        self.assertEqual(module.dependencies_id.mapped("name"), ["crm"])
        self.assertIn("BANT", module.description_html)
        self.assertNotIn("OFX", module.description_html)
