# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    attachment_index_content = fields.Text(
        string="Attachment Content",
        compute="_compute_attachment_index_content",
        store=True,
    )

    @api.depends("attachment_ids", "attachment_ids.index_content")
    def _compute_attachment_index_content(self):
        for ticket in self:
            contents = ticket.attachment_ids.mapped("index_content")
            # Filter out empty values and join with spaces
            ticket.attachment_index_content = " ".join([c for c in contents if c])
