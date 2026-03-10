from odoo import api, fields, models


class ESocialLotacaoTributaria(models.Model):
    _name = "l10n_br.esocial.lotacao.tributaria"
    _description = "eSocial Tabela 10 - Tipos de Lotação Tributária"
    _order = "codigo"

    codigo = fields.Char(size=2, required=True, index=True)
    nome = fields.Char(required=True)
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        ("codigo_uniq", "unique(codigo)", "Código da lotação deve ser único."),
    ]

    @api.depends("codigo", "nome")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.codigo} - {rec.nome}" if rec.codigo else rec.nome
