# Copyright 2023 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import requests

from odoo import fields, models


class HelpdeskConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    discord_webhook_url = fields.Char(
        string="Discord Webhook URL", config_parameter="helpdesk.discord_webhook_url"
    )

    def action_test_discord_webhook(self):
        webhook_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk.discord_webhook_url")
        )
        if webhook_url:
            data = {
                "content": "Teste de integração do webhook do Discord: \
                    A integração está funcionando corretamente."
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                webhook_url, json=data, headers=headers, timeout=200
            )
            if response.status_code == 204 or response.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Sucesso!",
                        "message": "Notificação de teste enviada com sucesso para o Discord.",
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Erro!",
                        "message": f"Falha ao enviar notificação para o \
                            Discord: {response.status_code} - {response.text}",
                        "type": "danger",
                        "sticky": False,
                    },
                }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Erro!",
                    "message": "URL do webhook do Discord não \
                        está configurada.",
                    "type": "danger",
                    "sticky": False,
                },
            }
