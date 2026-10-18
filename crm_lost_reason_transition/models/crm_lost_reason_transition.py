from odoo import api, fields, models


class CrmLostReasonTransition(models.Model):
    _name = "crm.lost.reason.transition"
    _description = "Transitioning Lost Leads by Reason and Stage"

    _sql_constraints = [
        (
            "unique_reason_stage",
            "unique(lost_reason_id, target_stage_id)",
            "There is already a transition configured "
            "for this loss reason and target stage.",
        )
    ]

    name = fields.Char(compute="_compute_name", store=True, readonly=True)
    lost_reason_id = fields.Many2one("crm.lost.reason", required=True)
    team_id = fields.Many2one("crm.team", required=True, string="Target Team")
    target_stage_id = fields.Many2one("crm.stage", required=True, string="Target Stage")

    @api.depends("lost_reason_id", "team_id", "target_stage_id")
    def _compute_name(self):
        for record in self:
            reason = record.lost_reason_id.name or "Unknown Reason"
            target_team = record.team_id.name or "Unknown Target Team"
            target_stage = record.target_stage_id.name or "Unknown Target Stage"
            record.name = f"{reason} | {target_team} / {target_stage}"
