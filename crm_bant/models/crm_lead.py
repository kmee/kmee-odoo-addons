from odoo import api, fields, models


class Lead(models.Model):
    _inherit = "crm.lead"

    # BUDGET fields
    bant_budget_status = fields.Selection(
        [
            ("undefined", "Undefined"),
            ("no_budget", "No Budget"),
            ("budget_defined", "Budget Defined"),
            ("budget_approved", "Budget Approved"),
        ],
        string="Budget Status",
        default="undefined",
        tracking=True,
    )

    bant_budget_amount = fields.Monetary(
        "Available Budget", currency_field="company_currency"
    )
    bant_budget_timeframe = fields.Selection(
        [
            ("current_quarter", "Current Quarter"),
            ("next_quarter", "Next Quarter"),
            ("current_year", "Current Year"),
            ("next_year", "Next Year"),
        ],
        string="Budget Timeframe",
        tracking=True,
    )

    # AUTHORITY fields
    bant_authority_status = fields.Selection(
        [
            ("undefined", "Undefined"),
            ("influencer", "Influencer"),
            ("recommender", "Recommender"),
            ("decision_maker", "Decision Maker"),
            ("approver", "Approver"),
        ],
        string="Authority Status",
        default="undefined",
        tracking=True,
    )

    bant_authority_contact = fields.Char("Authority Contact", tracking=True)
    bant_authority_role = fields.Char("Authority Role", tracking=True)
    bant_authority_notes = fields.Text("Authority Notes", tracking=True)

    # NEED fields
    bant_need_status = fields.Selection(
        [
            ("undefined", "Undefined"),
            ("nice_to_have", "Nice to Have"),
            ("important", "Important"),
            ("critical", "Critical"),
            ("strategic", "Strategic"),
        ],
        string="Need Status",
        default="undefined",
        tracking=True,
    )

    bant_need_description = fields.Text("Need Description")
    bant_need_pain_points = fields.Text("Pain Points")
    bant_need_success_criteria = fields.Text("Success Criteria")

    # TIMELINE fields
    bant_timeline_status = fields.Selection(
        [
            ("undefined", "Undefined"),
            ("no_timeline", "No Timeline"),
            ("long_term", "6+ Months"),
            ("medium_term", "3-6 Months"),
            ("short_term", "1-3 Months"),
            ("immediate", "<1 Month"),
        ],
        string="Timeline Status",
        default="undefined",
        tracking=True,
    )

    bant_timeline_date = fields.Date("Target Implementation Date", tracking=True)
    bant_timeline_reason = fields.Text("Timeline Reasoning", tracking=True)

    # BANT Score
    bant_budget_score = fields.Integer(
        "Budget Score", compute="_compute_bant_scores", store=True
    )
    bant_authority_score = fields.Integer(
        "Authority Score", compute="_compute_bant_scores", store=True
    )
    bant_need_score = fields.Integer(
        "Need Score", compute="_compute_bant_scores", store=True
    )
    bant_timeline_score = fields.Integer(
        "Timeline Score", compute="_compute_bant_scores", store=True
    )
    bant_total_score = fields.Integer(
        "BANT Score", compute="_compute_bant_total_score", store=True
    )
    bant_qualification_status = fields.Selection(
        [
            ("unqualified", "Unqualified"),
            ("partially_qualified", "Partially Qualified"),
            ("qualified", "Qualified"),
            ("fully_qualified", "Fully Qualified"),
        ],
        string="BANT Qualification",
        compute="_compute_bant_qualification",
        store=True,
    )

    # Progress bar for visualization
    bant_progress = fields.Integer("BANT Progress", compute="_compute_bant_progress")

    @api.depends(
        "bant_budget_status",
        "bant_authority_status",
        "bant_need_status",
        "bant_timeline_status",
    )
    def _compute_bant_scores(self):
        for lead in self:
            # Budget score calculation
            if lead.bant_budget_status == "budget_approved":
                lead.bant_budget_score = 3
            elif lead.bant_budget_status == "budget_defined":
                lead.bant_budget_score = 2
            elif lead.bant_budget_status == "no_budget":
                lead.bant_budget_score = 0
            else:
                lead.bant_budget_score = 0

            # Authority score calculation
            if (
                lead.bant_authority_status == "decision_maker"
                or lead.bant_authority_status == "approver"
            ):
                lead.bant_authority_score = 3
            elif lead.bant_authority_status == "recommender":
                lead.bant_authority_score = 2
            elif lead.bant_authority_status == "influencer":
                lead.bant_authority_score = 1
            else:
                lead.bant_authority_score = 0

            # Need score calculation
            if (
                lead.bant_need_status == "critical"
                or lead.bant_need_status == "strategic"
            ):
                lead.bant_need_score = 3
            elif lead.bant_need_status == "important":
                lead.bant_need_score = 2
            elif lead.bant_need_status == "nice_to_have":
                lead.bant_need_score = 1
            else:
                lead.bant_need_score = 0

            # Timeline score calculation
            if (
                lead.bant_timeline_status == "immediate"
                or lead.bant_timeline_status == "short_term"
            ):
                lead.bant_timeline_score = 3
            elif lead.bant_timeline_status == "medium_term":
                lead.bant_timeline_score = 2
            elif lead.bant_timeline_status == "long_term":
                lead.bant_timeline_score = 1
            else:
                lead.bant_timeline_score = 0

    @api.depends(
        "bant_budget_score",
        "bant_authority_score",
        "bant_need_score",
        "bant_timeline_score",
    )
    def _compute_bant_total_score(self):
        for lead in self:
            lead.bant_total_score = (
                lead.bant_budget_score
                + lead.bant_authority_score
                + lead.bant_need_score
                + lead.bant_timeline_score
            )

    @api.depends(
        "bant_total_score",
        "bant_budget_score",
        "bant_authority_score",
        "bant_need_score",
        "bant_timeline_score",
    )
    def _compute_bant_qualification(self):
        for lead in self:
            # Check if all dimensions have at least some value
            has_all_dimensions = all(
                [
                    lead.bant_budget_score > 0,
                    lead.bant_authority_score > 0,
                    lead.bant_need_score > 0,
                    lead.bant_timeline_score > 0,
                ]
            )

            # Calculate qualification status
            if lead.bant_total_score == 0:
                lead.bant_qualification_status = "unqualified"
            elif lead.bant_total_score < 6:
                lead.bant_qualification_status = "partially_qualified"
            elif lead.bant_total_score < 10:
                lead.bant_qualification_status = "qualified"
            else:
                # Only fully qualified if all dimensions have values and total score is high
                if has_all_dimensions:
                    lead.bant_qualification_status = "fully_qualified"
                else:
                    lead.bant_qualification_status = "qualified"

    def _compute_bant_progress(self):
        for lead in self:
            # Maximum possible score is 12 (3 points per dimension * 4 dimensions)
            lead.bant_progress = int((lead.bant_total_score / 12.0) * 100)
