from odoo import fields, models

STANDARD_SWIMLANES = [
    {"name": "Features", "color": "#714B67", "icon": "◆", "sequence": 10},
    {"name": "Bugs", "color": "#DC2626", "icon": "●", "sequence": 20},
    {"name": "Tech Debt", "color": "#D97706", "icon": "▲", "sequence": 30},
    {
        "name": "Expedite",
        "color": "#7C3AED",
        "icon": "⚡",
        "sequence": 40,
        "is_expedite": True,
        "wip_limit": 2,
    },
]

MINIMAL_SWIMLANES = [
    {"name": "Tasks", "color": "#714B67", "icon": "◆", "sequence": 10},
    {
        "name": "Expedite",
        "color": "#7C3AED",
        "icon": "⚡",
        "sequence": 20,
        "is_expedite": True,
    },
]


class SwimlaneTemplateWizard(models.TransientModel):
    _name = "project.kanban.swimlane.wizard"
    _description = "Wizard para criar swimlanes a partir de template"

    project_id = fields.Many2one(
        "project.project",
        string="Projeto",
        required=True,
    )
    template = fields.Selection(
        [
            ("standard", "Standard (Features, Bugs, Tech Debt, Expedite)"),
            ("minimal", "Minimal (Tasks, Expedite)"),
        ],
        string="Template",
        required=True,
        default="standard",
    )

    def action_apply(self):
        """Create swimlanes based on the selected template."""
        self.ensure_one()
        if self.template == "standard":
            swimlane_data = STANDARD_SWIMLANES
        else:
            swimlane_data = MINIMAL_SWIMLANES

        Swimlane = self.env["project.kanban.swimlane"]
        for vals in swimlane_data:
            Swimlane.create({**vals, "project_id": self.project_id.id})

        return {"type": "ir.actions.act_window_close"}
