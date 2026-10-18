# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProjectTask(models.Model):

    _inherit = "project.task"

    tech_lead_id = fields.Many2one("res.users", string="Tech Lead")

    @api.onchange("project_id")
    def _onchange_project_id(self):
        self.tech_lead_id = self.project_id.tech_lead_id
