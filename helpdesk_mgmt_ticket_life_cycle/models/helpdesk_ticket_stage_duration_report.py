# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


def display_duration(seconds, granularity=2):
    """Display duration in human readable format"""
    result = []
    intervals = (
        ("w", 604800),  # 60 * 60 * 24 * 7
        ("days", 86400),  # 60 * 60 * 24
        ("hours", 3600),  # 60 * 60
        ("min", 60),
        ("sec", 1),
    )
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    return ", ".join(result[:granularity])


class HelpdeskTicketStageDurationReport(models.Model):
    _name = "helpdesk.ticket.stage.duration.report"
    _description = "Helpdesk Ticket Stage Duration Report"
    _auto = False

    # Grouping fields
    team_id = fields.Many2one(
        comodel_name="helpdesk.ticket.team",
        string="Team",
        readonly=True,
    )
    stage_id = fields.Many2one(
        comodel_name="helpdesk.ticket.stage",
        string="Stage",
        readonly=True,
    )

    # Statistics fields
    ticket_count = fields.Integer(
        string="Number of Tickets",
        readonly=True,
    )

    total_duration_seconds = fields.Float(
        string="Total Duration (seconds)",
        readonly=True,
    )

    avg_duration_seconds = fields.Float(
        string="Average Duration (seconds)",
        readonly=True,
    )

    avg_duration_display = fields.Char(
        string="Average Duration",
        compute="_compute_duration_display",
        store=False,
    )

    min_duration_seconds = fields.Float(
        string="Min Duration (seconds)",
        readonly=True,
    )

    max_duration_seconds = fields.Float(
        string="Max Duration (seconds)",
        readonly=True,
    )

    # Additional metrics
    completed_tickets = fields.Integer(
        string="Completed Tickets",
        readonly=True,
    )

    active_tickets = fields.Integer(
        string="Active Tickets",
        readonly=True,
    )

    completion_rate = fields.Float(
        string="Completion Rate (%)",
        readonly=True,
    )

    @api.depends("avg_duration_seconds")
    def _compute_duration_display(self):
        for record in self:
            if record.avg_duration_seconds > 0:
                record.avg_duration_display = display_duration(
                    record.avg_duration_seconds, 3
                )
            else:
                record.avg_duration_display = ""

    def init(self):
        """Initialize the report view"""
        tools.drop_view_if_exists(self._cr, "helpdesk_ticket_stage_duration_report")
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW helpdesk_ticket_stage_duration_report AS (
                WITH stage_stats AS (
                    SELECT
                        team_id,
                        stage_id,
                        COUNT(*) as ticket_count,
                        SUM(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) as total_duration_seconds,
                        AVG(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) as avg_duration_seconds,
                        MIN(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) as min_duration_seconds,
                        MAX(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) as max_duration_seconds,
                        COUNT(CASE WHEN end_date IS NOT NULL THEN 1 END) as completed_tickets,
                        COUNT(CASE WHEN end_date IS NULL THEN 1 END) as active_tickets
                    FROM helpdesk_ticket_stage_duration
                    WHERE start_date IS NOT NULL
                    GROUP BY team_id, stage_id
                )
                SELECT
                    ROW_NUMBER() OVER () as id,
                    team_id,
                    stage_id,
                    ticket_count,
                    total_duration_seconds,
                    avg_duration_seconds,
                    min_duration_seconds,
                    max_duration_seconds,
                    completed_tickets,
                    active_tickets,
                    CASE
                        WHEN ticket_count > 0 THEN
                            (completed_tickets::float / ticket_count::float) * 100
                        ELSE 0
                    END as completion_rate
                FROM stage_stats
                WHERE ticket_count > 0
                ORDER BY team_id, stage_id
            )
            """
        )
