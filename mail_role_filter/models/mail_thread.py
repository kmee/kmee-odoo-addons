# Copyright https://kmee.com.br/ KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients_data = super()._notify_get_recipients(message, msg_vals, **kwargs)
        if not recipients_data:
            return recipients_data

        model_name = self._name
        roles = (
            self.env["mail.role.filter"]
            .sudo()
            .search([("model_id.model", "=", model_name), ("active", "=", True)])
            .mapped("role_id")
        )
        if not roles:
            return recipients_data

        recipients_data_filtered = []
        for recipient in recipients_data:
            for role in roles:
                partner_id = self.env["res.partner"].browse(recipient["id"])
                user_id = (
                    self.env["res.users"]
                    .sudo()
                    .search([("partner_id", "=", partner_id.id)])
                )
                if role.id in user_id.role_ids.mapped("id"):
                    recipients_data_filtered.append(recipient)

        seen = set()
        recipients_data_filtered = [
            d
            for d in recipients_data_filtered
            if d["id"] not in seen and not seen.add(d["id"])
        ]
        return recipients_data_filtered
