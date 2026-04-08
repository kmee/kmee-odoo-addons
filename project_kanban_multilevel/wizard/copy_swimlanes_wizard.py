from odoo import fields, models


class CopySwimlinesWizard(models.TransientModel):
    _name = "project.kanban.copy.swimlanes.wizard"
    _description = "Wizard para copiar swimlanes de outro projeto"

    target_project_id = fields.Many2one(
        "project.project",
        string="Projeto Destino",
        required=True,
    )
    source_project_id = fields.Many2one(
        "project.project",
        string="Projeto Origem",
        required=True,
        domain="[('swimlane_ids', '!=', False)]",
    )

    def action_copy(self):
        """Copy swimlanes from source project to target project."""
        self.ensure_one()
        Swimlane = self.env["project.kanban.swimlane"]
        for src in self.source_project_id.swimlane_ids:
            Swimlane.create(
                {
                    "name": src.name,
                    "sequence": src.sequence,
                    "color": src.color,
                    "icon": src.icon,
                    "is_expedite": src.is_expedite,
                    "wip_limit": src.wip_limit,
                    "project_id": self.target_project_id.id,
                }
            )

        return {"type": "ir.actions.act_window_close"}
