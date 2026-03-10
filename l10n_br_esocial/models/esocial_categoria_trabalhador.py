from odoo import api, fields, models


class ESocialCategoriaTrabalhador(models.Model):
    _name = "l10n_br.esocial.categoria.trabalhador"
    _description = "eSocial Tabela 1 - Categoria do Trabalhador"
    _order = "codigo"

    codigo = fields.Char(size=3, required=True, index=True)
    nome = fields.Char(required=True)
    grupo = fields.Selection(
        [
            ("1", "Empregado/Temporário"),
            ("2", "Avulso"),
            ("3", "Agente Público"),
            ("4", "Cessão"),
            ("7", "Contribuinte Individual"),
            ("9", "Bolsista"),
        ],
    )
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        ("codigo_uniq", "unique(codigo)", "Código da categoria deve ser único."),
    ]

    @api.depends("codigo", "nome")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.codigo} - {rec.nome}" if rec.codigo else rec.nome
