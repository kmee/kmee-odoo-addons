from odoo import api, fields, models


class ESocialTabelaMixin(models.AbstractModel):
    _name = "l10n_br.esocial.tabela.mixin"
    _description = "eSocial Tabela Base"
    _order = "codigo"

    codigo = fields.Char(required=True, index=True)
    nome = fields.Char(required=True)
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("codigo", "nome")
    def _compute_name(self):
        for rec in self:
            if rec.codigo and rec.nome:
                rec.name = f"[{rec.codigo}] {rec.nome}"
            else:
                rec.name = rec.nome or rec.codigo or ""
