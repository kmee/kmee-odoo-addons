# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrLeave(models.Model):

    _inherit = "hr.leave"

    @api.model_create_multi
    def create(self, vals_list):
        self = self.with_context(mail_auto_subscribe_no_notify=True)
        return super(HrLeave, self).create(vals_list)

    def write(self, vals):
        self = self.with_context(mail_auto_subscribe_no_notify=True)
        return super(HrLeave, self).write(vals)
