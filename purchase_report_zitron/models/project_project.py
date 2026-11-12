# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    zitron_project_number = fields.Char(
        string="Número do projeto",
        index="btree_not_null",
        copy=False,
        tracking=True,
        help="Official project number (e.g. 70.000.001), printed on the "
        "purchase order PDF.",
    )
