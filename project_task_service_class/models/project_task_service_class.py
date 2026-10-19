# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProjectTaskServiceClass(models.Model):

    _name = "project.task.service.class"
    _description = "Project Task Service Class"  # TODO

    name = fields.Char(required=True)
    color = fields.Integer()
