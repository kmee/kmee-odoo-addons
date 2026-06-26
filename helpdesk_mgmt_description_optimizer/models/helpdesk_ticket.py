# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["helpdesk.ticket", "html.optimizer.mixin"]

    description_summary = fields.Html(
        string="Description Summary",
        sanitize=False,
        compute="_compute_description_summary",
        store=True,
        copy=False,
    )
    has_description_full = fields.Boolean(
        compute="_compute_has_description_full",
    )

    @api.depends("description")
    def _compute_description_summary(self):
        for ticket in self:
            ticket.description_summary = ticket._optimizer_summary(ticket.description)

    @api.depends("description")
    def _compute_has_description_full(self):
        for ticket in self:
            ticket.has_description_full = ticket._optimizer_has_more(ticket.description)
