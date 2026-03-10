from odoo import api, fields, models


class ESocialMotivoAfastamento(models.Model):
    _name = "l10n_br.esocial.motivo.afastamento"
    _description = "eSocial Tabela 18 - Motivos de Afastamento"
    _order = "codigo"

    codigo = fields.Char(size=2, required=True, index=True)
    nome = fields.Char(required=True)
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        (
            "codigo_uniq",
            "unique(codigo)",
            "Código do motivo de afastamento deve ser único.",
        ),
    ]

    @api.depends("codigo", "nome")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.codigo} - {rec.nome}" if rec.codigo else rec.nome
