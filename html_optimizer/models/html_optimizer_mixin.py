# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

from ..tools.html_sanitizer import HtmlSanitizer


class HtmlOptimizerMixin(models.AbstractModel):
    _name = "html.optimizer.mixin"
    _description = "HTML Optimizer Mixin"

    def _optimizer_sanitizer(self):
        return HtmlSanitizer()

    def _optimizer_summary(self, value):
        if not value:
            return value
        sanitizer = self._optimizer_sanitizer()
        return sanitizer.create_summary(sanitizer.optimize(value))

    def _optimizer_has_more(self, value):
        if not value:
            return False
        return self._optimizer_sanitizer().has_hidden_content(value)
