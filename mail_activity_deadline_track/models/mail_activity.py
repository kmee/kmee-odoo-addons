# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def write(self, vals):
        if "date_deadline" in vals:
            for activity in self:
                if str(activity.date_deadline) != str(vals["date_deadline"]):
                    self.env[activity.res_model].browse(activity.res_id).message_post(
                        body=_(
                            "Deadline alterado: %(summary)s<br/>%(old)s -> %(new)s",
                            summary=activity.summary
                            or activity.activity_type_id.name
                            or "",
                            old=activity.date_deadline,
                            new=vals["date_deadline"],
                        )
                    )
        return super().write(vals)
