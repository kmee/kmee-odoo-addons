from odoo import fields, models


class CrmLostReasonTransition(models.Model):
    _name = "crm.lost.reason.transition"
    _description = "Transitioning Lost Leads by Reason and Stage"

    lost_reason_id = fields.Many2one("crm.lost.reason", required=True)
    source_stage_id = fields.Many2one("crm.stage", required=True, string="Source Stage")
    team_id = fields.Many2one("crm.team", required=True, string="Target Team")
    target_stage_id = fields.Many2one("crm.stage", required=True, string="Target Stage")

    _sql_constraints = [
        (
            "unique_reason_stage",
            "unique(lost_reason_id, source_stage_id)",
            "_(There is already a transition configured"
            "for this loss reason and source stage.)",
        )
    ]
