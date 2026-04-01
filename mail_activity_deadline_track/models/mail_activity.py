# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def write(self, vals):
        if "date_deadline" in vals:
            for activity in self:
                if str(activity.date_deadline) != str(vals["date_deadline"]):
                    record = self.env[activity.res_model].browse(activity.res_id)
                    summary = (
                        activity.summary or activity.activity_type_id.name or ""
                    )
                    record.message_post(
                        body=(
                            f"Deadline alterado: {summary}"
                            f"<br/>{activity.date_deadline} -> "
                            f"{vals['date_deadline']}"
                        ),
                    )
        return super().write(vals)
