# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProjectProject(models.Model):

    _inherit = "project.project"

    tech_lead_id = fields.Many2one("res.users", string="Tech Lead")
