from odoo import api, fields, models


class ESocialNaturezaRubrica(models.Model):
    _name = "l10n_br.esocial.natureza.rubrica"
    _description = "eSocial Tabela 3 - Natureza da Rubrica"
    _order = "codigo"

    codigo = fields.Char(size=4, required=True, index=True)
    nome = fields.Char(required=True)
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        (
            "codigo_uniq",
            "unique(codigo)",
            "Código da natureza de rubrica deve ser único.",
        ),
    ]

    @api.depends("codigo", "nome")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.codigo} - {rec.nome}" if rec.codigo else rec.nome
