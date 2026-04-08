from odoo import api, fields, models


class ProjectKanbanSwimlane(models.Model):
    _name = "project.kanban.swimlane"
    _description = "Kanban Swimlane"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    color = fields.Char(string="Cor hex", default="#714B67")
    icon = fields.Char(string="Ícone", default="◆")
    project_id = fields.Many2one(
        "project.project",
        required=True,
        ondelete="cascade",
    )
    is_expedite = fields.Boolean(
        string="É Expedite",
        default=False,
        help="Swimlane de prioridade máxima.",
    )
    wip_limit = fields.Integer(
        string="WIP Limit da lane",
        default=0,
        help="0 = sem limite",
    )
    fold = fields.Boolean(string="Colapsada", default=False)
    task_count = fields.Integer(
        string="Tarefas",
        compute="_compute_task_count",
    )

    _sql_constraints = [
        (
            "unique_name_project",
            "UNIQUE(name, project_id)",
            "O nome da swimlane deve ser único por projeto.",
        ),
    ]

    @api.depends()
    def _compute_task_count(self):
        task_data = self.env["project.task"]._read_group(
            [("swimlane_id", "in", self.ids)],
            ["swimlane_id"],
            ["__count"],
        )
        counts = {swimlane.id: count for swimlane, count in task_data}
        for rec in self:
            rec.task_count = counts.get(rec.id, 0)
