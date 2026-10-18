# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReportProjectTaskUser(models.Model):

    _inherit = "report.project.task.user"

    service_class_id = fields.Many2one(
        "project.task.service.class", string="Classe de Serviço", readonly=True
    )

    def _select(self):
        return super()._select() + ", t.service_class_id"

    def _group_by(self):
        return super()._group_by() + ", t.service_class_id"
