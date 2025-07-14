# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailFilterRole(models.Model):

    _name = "mail.role.filter"
    _description = "Email sending filter by Role and Model"

    role_id = fields.Many2one("res.users.role", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    active = fields.Boolean(default=True)
