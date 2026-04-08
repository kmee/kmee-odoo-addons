from odoo import api, fields, models


class ProjectPortfolio(models.Model):
    _name = "project.portfolio"
    _description = "Project Portfolio"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Html()
    project_ids = fields.Many2many("project.project", string="Projetos")
    project_count = fields.Integer(compute="_compute_project_count")
    task_count = fields.Integer(compute="_compute_task_count")
    active = fields.Boolean(default=True)
    color = fields.Integer()

    @api.depends("project_ids")
    def _compute_project_count(self):
        for portfolio in self:
            portfolio.project_count = len(portfolio.project_ids)

    @api.depends("project_ids")
    def _compute_task_count(self):
        Task = self.env["project.task"]
        for portfolio in self:
            if portfolio.project_ids:
                portfolio.task_count = Task.search_count(
                    [("project_id", "in", portfolio.project_ids.ids)]
                )
            else:
                portfolio.task_count = 0

    def action_open_projects(self):
        self.ensure_one()
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", self.project_ids.ids)],
            "context": {"default_portfolio_id": self.id},
        }

    def action_view_all_tasks(self):
        self.ensure_one()
        return {
            "name": f"{self.name} — Tarefas",
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "kanban_multilevel,kanban,list,form",
            "domain": [("project_id", "in", self.project_ids.ids)],
            "context": {
                "portfolio_mode": True,
                "portfolio_project_ids": self.project_ids.ids,
            },
        }
