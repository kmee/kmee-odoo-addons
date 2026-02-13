# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>

from odoo import api, fields, models


def display_duration(seconds, granularity=2):
    result = []
    intervals = (
        ("w", 604800),
        ("days", 86400),
        ("hours", 3600),
        ("min", 60),
        ("sec", 1),
    )
    remaining_seconds = max(seconds or 0.0, 0.0)
    for name, count in intervals:
        value = int(remaining_seconds // count)
        if value:
            remaining_seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append(f"{value} {name}")
    return ", ".join(result[:granularity])


class CrmLeadStageDuration(models.Model):
    _name = "crm.lead.stage.duration"
    _description = "CRM Lead Stage Duration"
    _order = "start_date desc, id desc"

    _sql_constraints = [
        (
            "check_end_after_start",
            "CHECK(end_date IS NULL OR end_date >= start_date)",
            "The end date must be greater than or equal to start date.",
        ),
    ]

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="Opportunity",
        required=True,
        ondelete="cascade",
        index=True,
    )
    stage_id = fields.Many2one(
        comodel_name="crm.stage",
        string="Stage",
        required=True,
        index=True,
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Changed By",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    start_date = fields.Datetime(
        string="Start Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    end_date = fields.Datetime(
        string="End Date",
        index=True,
    )
    running = fields.Boolean(
        string="Running",
        compute="_compute_running",
        store=True,
    )
    duration_seconds = fields.Float(
        string="Duration (seconds)",
        compute="_compute_duration",
    )
    duration_display = fields.Char(
        string="Duration",
        compute="_compute_duration",
    )

    @api.depends("end_date")
    def _compute_running(self):
        for record in self:
            record.running = not bool(record.end_date)

    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        now = fields.Datetime.now()
        for record in self:
            duration_seconds = 0.0
            if record.start_date:
                stop_date = record.end_date or now
                duration_seconds = (stop_date - record.start_date).total_seconds()
            record.duration_seconds = max(duration_seconds, 0.0)
            record.duration_display = (
                display_duration(record.duration_seconds, 4)
                if record.duration_seconds
                else ""
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("lead_id") and not vals.get("team_id"):
                lead = self.env["crm.lead"].browse(vals["lead_id"])
                vals["team_id"] = lead.team_id.id
        return super().create(vals_list)
