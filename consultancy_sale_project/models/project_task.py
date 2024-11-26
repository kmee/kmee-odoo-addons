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

    @api.onchange("timesheet_ids")
    def _onchange_employee_id(self):
        if self.project_id:
            project = self.project_id

            employee_indices = {}

            for timesheet in self.timesheet_ids:
                employee = timesheet.employee_id
                if employee:
                    sale_line_employee = project.sale_line_employee_ids.filtered(
                        lambda line: line.employee_id == employee
                    )

                    if sale_line_employee:
                        current_index = employee_indices.get(employee.id, 0)

                        if len(sale_line_employee) > current_index:
                            available_line = sale_line_employee[current_index]
                            timesheet.contract_line_id = available_line.contract_line_id

                            employee_indices[employee.id] = current_index + 1
                        else:
                            timesheet.contract_line_id = False
