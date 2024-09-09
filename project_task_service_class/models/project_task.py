# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProjectTask(models.Model):

    _inherit = "project.task"

    service_class_id = fields.Many2one(
        "project.task.service.class", string="Classe de Serviço"
    )

    @api.onchange("service_class_id")
    def _onchange_service_class_id(self):
        self.color = self.service_class_id.color
