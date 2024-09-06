from odoo import api, models


class Task(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, vals):
        task = super(Task, self).default_get(vals)
        project_id = self.env.context.get("default_project_id")
        project = self.env["project.project"].browse(project_id)
        task.update(
            {
                "contract_id": project.contract_id.id,
                "contract_line_id": project.contract_line_id.id,
            }
        )
        return task
