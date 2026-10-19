# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def action_quotation_send(self):
        if self.detect_exceptions():
            return self._popup_exceptions()
        return super().action_quotation_send()
