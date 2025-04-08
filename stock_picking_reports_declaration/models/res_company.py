# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    declaration_receipt = fields.Html(
        string="Declaration of Receipt",
        help="Text displayed in the declaration area of ​​the report.",
    )
