# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL


class ReportProjectTaskUser(models.Model):

    _inherit = "report.project.task.user"

    service_class_id = fields.Many2one(
        "project.task.service.class", string="Classe de Serviço", readonly=True
    )

    def _select(self):
        return SQL("%s, t.service_class_id", super()._select())

    def _group_by(self):
        return SQL("%s, t.service_class_id", super()._group_by())
