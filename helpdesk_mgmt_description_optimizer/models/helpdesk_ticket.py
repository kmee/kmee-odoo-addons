# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["helpdesk.ticket", "html.optimizer.mixin"]

    _optimizer_fields = {"description": "description_full"}

    description_full = fields.Html(
        string="Full Description",
        sanitize=False,
        copy=False,
    )
    has_description_full = fields.Boolean(
        compute="_compute_has_description_full",
    )

    @api.depends("description_full")
    def _compute_has_description_full(self):
        for ticket in self:
            ticket.has_description_full = ticket._optimizer_has_full("description_full")

    def action_reprocess_descriptions(self):
        """Enqueue a background job that re-optimizes existing tickets."""
        self.env["helpdesk.ticket"].with_delay(
            description="Reprocess helpdesk descriptions"
        )._optimizer_reprocess()
