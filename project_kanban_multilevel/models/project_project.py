from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    use_multilevel_kanban = fields.Boolean(
        string="Kanban Multinível",
        default=False,
    )
    show_initiatives_lane = fields.Boolean(
        string="Mostrar Initiatives",
        default=True,
    )
    aging_threshold = fields.Integer(
        string="Aging Threshold (dias)",
        default=5,
        help="Número de dias no mesmo estágio para considerar a tarefa em aging.",
    )
    portfolio_id = fields.Many2one("project.portfolio", string="Portfolio")
    swimlane_ids = fields.One2many(
        "project.kanban.swimlane",
        "project_id",
        string="Swimlanes",
    )

    def action_create_swimlanes_from_template(self):
        """Open the swimlane template wizard for this project."""
        self.ensure_one()
        return {
            "name": "Criar Swimlanes a partir de Template",
            "type": "ir.actions.act_window",
            "res_model": "project.kanban.swimlane.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_copy_swimlanes(self):
        """Open the copy swimlanes wizard for this project."""
        self.ensure_one()
        return {
            "name": "Copiar Swimlanes de Outro Projeto",
            "type": "ir.actions.act_window",
            "res_model": "project.kanban.copy.swimlanes.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_target_project_id": self.id},
        }
