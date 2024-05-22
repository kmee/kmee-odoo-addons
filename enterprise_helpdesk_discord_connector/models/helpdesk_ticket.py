# Copyright 2023 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import requests

from odoo import api, models
from odoo.tools import html2plaintext


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    @api.model
    def create(self, vals):
        ticket = super(HelpdeskTicket, self).create(vals)
        self.send_discord_notification(ticket)
        return ticket

    def send_discord_notification(self, ticket):
        webhook_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk.discord_webhook_url")
        )
        if webhook_url:
            description = html2plaintext(ticket.description or "")
            data = {
                "content": f"Novo ticket criado:\n**Título:** {ticket.name}\
                \n**Cliente:** {ticket.partner_id.name}\
                \n**Responsável:** {ticket.user_id.name or 'N/A'}\
                \n**Descrição:** {description}"
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                webhook_url, json=data, headers=headers, timeout=200
            )

            if response.status_code != 202 or 200:
                pass
