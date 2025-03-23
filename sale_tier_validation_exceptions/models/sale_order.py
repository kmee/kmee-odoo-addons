# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def action_quotation_send(self):
        if self.detect_exceptions():
            return self._popup_exceptions()
        return super().action_quotation_send()

    def validate_tier(self):
        super(SaleOrder, self).validate_tier()
        self.action_ignore_exceptions()
        return True

    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        exception_fields = super(SaleOrder, self)._get_validation_exceptions(
            extra_domain, add_base_exceptions
        )
        return exception_fields + ["ignore_exception", "exception_ids"]
