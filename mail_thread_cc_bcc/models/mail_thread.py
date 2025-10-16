# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        email_cc = message_dict.get("cc", "")
        email_cco = message_dict.get("bcc", "")
        all_cc = ",".join(filter(None, [email_cc, email_cco]))
        if all_cc:
            self.env["mail.thread"]._get_cc_localparts(all_cc)
            current_recipients = message_dict.get("recipients", "")
            message_dict["recipients"] = (
                f"{current_recipients},{all_cc}" if current_recipients else all_cc
            )
        return super().message_route(
            message, message_dict, model, thread_id, custom_values
        )
