# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools

from .crm_lead_stage_duration import display_duration


class CrmLeadStageDurationReport(models.Model):
    _name = "crm.lead.stage.duration.report"
    _description = "CRM Lead Stage Duration Report"
    _auto = False

    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        readonly=True,
    )
    stage_id = fields.Many2one(
        comodel_name="crm.stage",
        string="Stage",
        readonly=True,
    )
    line_count = fields.Integer(
        string="Transitions",
        readonly=True,
    )
    lead_count = fields.Integer(
        string="Opportunities",
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
        compute="_compute_avg_duration_display",
    )
    min_duration_seconds = fields.Float(
        string="Min Duration (seconds)",
        readonly=True,
    )
    max_duration_seconds = fields.Float(
        string="Max Duration (seconds)",
        readonly=True,
    )
    closed_line_count = fields.Integer(
        string="Closed Transitions",
        readonly=True,
    )
    running_line_count = fields.Integer(
        string="Running Transitions",
        readonly=True,
    )

    @api.depends("avg_duration_seconds")
    def _compute_avg_duration_display(self):
        for record in self:
            record.avg_duration_display = (
                display_duration(record.avg_duration_seconds, 3)
                if record.avg_duration_seconds
                else ""
            )

    def init(self):
        tools.drop_view_if_exists(self._cr, "crm_lead_stage_duration_report")
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW crm_lead_stage_duration_report AS (
                WITH stage_stats AS (
                    SELECT
                        team_id,
                        stage_id,
                        COUNT(*) AS line_count,
                        COUNT(DISTINCT lead_id) AS lead_count,
                        SUM(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) AS total_duration_seconds,
                        AVG(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) AS avg_duration_seconds,
                        MIN(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) AS min_duration_seconds,
                        MAX(CASE WHEN end_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (end_date - start_date))
                        ELSE
                            EXTRACT(EPOCH FROM (NOW() - start_date))
                        END) AS max_duration_seconds,
                        COUNT(CASE WHEN end_date IS NOT NULL THEN 1 END) AS closed_line_count,
                        COUNT(CASE WHEN end_date IS NULL THEN 1 END) AS running_line_count
                    FROM crm_lead_stage_duration
                    WHERE start_date IS NOT NULL
                    GROUP BY team_id, stage_id
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    team_id,
                    stage_id,
                    line_count,
                    lead_count,
                    total_duration_seconds,
                    avg_duration_seconds,
                    min_duration_seconds,
                    max_duration_seconds,
                    closed_line_count,
                    running_line_count
                FROM stage_stats
                WHERE line_count > 0
            )
            """
        )
