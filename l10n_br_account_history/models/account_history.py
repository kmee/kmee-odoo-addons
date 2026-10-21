# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

# Variaveis aceitas no template do historico. A substituicao e literal, sem
# expressao nem condicional, de proposito: historico e texto de escrituracao,
# nao lugar de logica. O que nao couber aqui e caso para codigo no consumidor.
PLACEHOLDERS = {
    "%{DD}": lambda ctx: ctx["date"] and ctx["date"].strftime("%d") or "",
    "%{MM}": lambda ctx: ctx["date"] and ctx["date"].strftime("%m") or "",
    "%{AA}": lambda ctx: ctx["date"] and ctx["date"].strftime("%y") or "",
    "%{AAAA}": lambda ctx: ctx["date"] and ctx["date"].strftime("%Y") or "",
    "%{DOC}": lambda ctx: ctx.get("doc") or "",
    "%{PARCEIRO}": lambda ctx: ctx.get("partner") or "",
    "%{CAMPO}": lambda ctx: ctx.get("field_label") or "",
    "%{LINHA}": lambda ctx: ctx.get("line_name") or "",
}


class AccountHistory(models.Model):
    """Historico padrao dos lancamentos contabeis.

    Padroniza o texto que vai nas partidas: em vez de cada rotina montar o
    proprio historico, o texto vem de um template com variaveis de data,
    documento e parceiro. E o mesmo historico que os sistemas dos escritorios
    esperam (com codigo proprio no destino) e que o SPED Contabil carrega nos
    registros I200/I250.
    """

    _name = "l10n_br.account.history"
    _description = "Historico Padrao Contabil"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        help="Vazio vale para todas as empresas.",
    )
    template = fields.Char(
        string="Template do historico",
        required=True,
        help="Texto com variaveis: %{DD} %{MM} %{AA} %{AAAA} (data), "
        "%{DOC} (documento), %{PARCEIRO} (nome do parceiro), "
        "%{CAMPO} (rotulo do campo de origem) e %{LINHA} (descricao da linha).",
    )
    code = fields.Char(
        string="Codigo no sistema contabil",
        size=20,
        help="Codigo deste historico padrao no sistema do escritorio de "
        "contabilidade, quando o layout de exportacao usar codigo de "
        "historico.",
    )

    def render(
        self, date=None, doc=None, partner=None, field_label=None, line_name=None
    ):
        """Devolve o texto do historico com as variaveis substituidas."""
        self.ensure_one()
        ctx = {
            "date": date,
            "doc": doc,
            "partner": partner,
            "field_label": field_label,
            "line_name": line_name,
        }
        text = self.template or ""
        for token, resolver in PLACEHOLDERS.items():
            if token in text:
                text = text.replace(token, resolver(ctx))
        return " ".join(text.split())

    @api.model
    def render_for_move_line(self, history, move, line_name=None, field_label=None):
        """Atalho para o caso comum: historico a partir de um account.move."""
        if not history:
            return ""
        return history.render(
            date=move.date,
            doc=move.ref or move.name,
            partner=move.partner_id.display_name,
            field_label=field_label,
            line_name=line_name,
        )
