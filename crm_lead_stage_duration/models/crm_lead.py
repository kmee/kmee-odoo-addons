# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .crm_lead_stage_duration import display_duration


class CrmLead(models.Model):
    _inherit = "crm.lead"

    stage_duration_ids = fields.One2many(
        comodel_name="crm.lead.stage.duration",
        inverse_name="lead_id",
        string="Stage Durations",
        copy=False,
    )
    current_stage_total_duration_seconds = fields.Float(
        string="Current Stage Total Duration (seconds)",
        compute="_compute_current_stage_total_duration",
    )
    current_stage_total_duration = fields.Char(
        string="Current Stage Total Duration",
        compute="_compute_current_stage_total_duration",
    )

    @api.depends(
        "stage_id",
        "stage_duration_ids.stage_id",
        "stage_duration_ids.start_date",
        "stage_duration_ids.end_date",
    )
    def _compute_current_stage_total_duration(self):
        now = fields.Datetime.now()
        for lead in self:
            total_seconds = 0.0
            if lead.stage_id:
                stage_lines = lead.stage_duration_ids.filtered(
                    lambda line: line.stage_id == lead.stage_id
                )
                for line in stage_lines:
                    if not line.start_date:
                        continue
                    stop_date = line.end_date or now
                    total_seconds += (stop_date - line.start_date).total_seconds()
            lead.current_stage_total_duration_seconds = max(total_seconds, 0.0)
            lead.current_stage_total_duration = (
                display_duration(total_seconds, 4) if total_seconds else ""
            )

    def _close_stage_duration_line(self, end_date=None):
        end_date = end_date or fields.Datetime.now()
        open_lines = self.env["crm.lead.stage.duration"].search(
            [("lead_id", "in", self.ids), ("end_date", "=", False)]
        )
        if open_lines:
            open_lines.write({"end_date": end_date})

    def _open_stage_duration_line(self, start_date=None):
        start_date = start_date or fields.Datetime.now()
        values = []
        for lead in self.filtered("stage_id"):
            values.append(
                {
                    "lead_id": lead.id,
                    "stage_id": lead.stage_id.id,
                    "team_id": lead.team_id.id,
                    "user_id": self.env.user.id,
                    "start_date": start_date,
                }
            )
        if values:
            self.env["crm.lead.stage.duration"].create(values)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        now = fields.Datetime.now()
        leads._close_stage_duration_line(end_date=now)
        leads._open_stage_duration_line(start_date=now)
        return leads

    def write(self, vals):
        previous_stage_by_lead = {}
        if "stage_id" in vals:
            previous_stage_by_lead = {lead.id: lead.stage_id.id for lead in self}

        result = super().write(vals)

        if previous_stage_by_lead:
            changed_leads = self.filtered(
                lambda lead: previous_stage_by_lead.get(lead.id) != lead.stage_id.id
            )
            if changed_leads:
                now = fields.Datetime.now()
                changed_leads._close_stage_duration_line(end_date=now)
                changed_leads._open_stage_duration_line(start_date=now)
        return result
