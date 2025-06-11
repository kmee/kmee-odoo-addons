from odoo import _, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def write(self, vals):
        res = super().write(vals)
        if "lost_reason" in vals:
            for lead in self:
                if not lead.active:
                    lead._apply_lost_reason_transition()
        return res

    def action_set_lost(self, **kwargs):
        res = super().action_set_lost(**kwargs)
        for lead in self:
            if not lead.lost_reason_id:
                raise UserError(
                    _("_(Please, select a lost reason before mark lead as lost.)")
                )
            lead._apply_lost_reason_transition()
        return res

    def _apply_lost_reason_transition(self):
        for lead in self:
            if not lead.lost_reason_id:
                return
            transition = self.env["crm.lost.reason.transition"].search(
                [
                    ("lost_reason_id", "=", lead.lost_reason_id.id),
                    ("source_stage_id", "=", lead.stage_id.id),
                ],
                limit=1,
            )
            if transition:
                lead.write(
                    {
                        "team_id": transition.team_id.id,
                        "stage_id": transition.target_stage_id.id,
                    }
                )
