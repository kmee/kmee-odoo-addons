# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    expected_margin_percent = fields.Float(
        string="Margem Esperada (%)",
        digits=(5, 2),
        help="Margem percentual esperada para este produto. "
        "Usado para comparação com a margem calculada real.",
    )
    expected_markup_percent = fields.Float(
        string="Markup Esperado (%)",
        digits=(5, 2),
        help="Markup percentual esperado para este produto. "
        "Usado para comparação com o markup calculado real.",
    )

    @api.onchange("expected_margin_percent")
    def _onchange_expected_margin_percent(self):
        """Calcula o markup esperado baseado na margem esperada."""
        if self.expected_margin_percent and self.expected_margin_percent != 100:
            # Fórmula: Markup = Margem / (100 - Margem) * 100
            self.expected_markup_percent = (
                self.expected_margin_percent
                / (100 - self.expected_margin_percent)
                * 100
            )

    @api.onchange("expected_markup_percent")
    def _onchange_expected_markup_percent(self):
        """Calcula a margem esperada baseada no markup esperado."""
        if self.expected_markup_percent:
            # Fórmula: Margem = Markup / (100 + Markup) * 100
            self.expected_margin_percent = (
                self.expected_markup_percent
                / (100 + self.expected_markup_percent)
                * 100
            )
