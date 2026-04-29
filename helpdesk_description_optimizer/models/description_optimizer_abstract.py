from odoo import api, fields, models

from .html_sanitizer import HtmlSanitizer


class DescriptionOptimizerAbstract(models.AbstractModel):
    """Modelo abstract para adicionar otimização de descrição."""

    _name = "description.optimizer.abstract"
    _description = "Description Optimizer Abstract"

    description_full = fields.Html(
        string="Descrição Completa",
        sanitize=False,
    )

    def _sanitize_description(self, description):
        """Aplica sanitização ao HTML da descrição."""
        if not description:
            return description, description

        sanitizer = HtmlSanitizer()
        sanitized = sanitizer.sanitize(description)
        return sanitized, description

    @api.model
    def create(self, vals_list):
        """Override de create para salvar description_full e sanitizar description."""
        for vals in vals_list if isinstance(vals_list, list) else [vals_list]:
            if "description" in vals and vals["description"]:
                sanitized, original = self._sanitize_description(vals["description"])
                vals["description"] = sanitized
                vals["description_full"] = original
        return super().create(vals_list)

    def write(self, vals):
        """Override de write para salvar description_full e sanitizar description."""
        if "description" in vals and vals["description"]:
            sanitized, original = self._sanitize_description(vals["description"])
            vals["description"] = sanitized
            vals["description_full"] = original
        return super().write(vals)
