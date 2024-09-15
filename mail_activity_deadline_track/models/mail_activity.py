# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailActity(models.Model):
    _inherit = "mail.activity"

    def write(self, vals):
        if "date_deadline" in vals:
            if self.date_deadline != vals["date_deadline"]:
                self.env[self.res_model].browse(self.res_id).message_post(
                    body=f"""Deadline alterado: {
                        self.summary or self.activity_type_id.name or ""
                        } \n {self.date_deadline} -> {vals['date_deadline']}"""
                )
        return super(MailActity, self).write(vals)
