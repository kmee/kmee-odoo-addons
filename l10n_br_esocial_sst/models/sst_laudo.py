# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBrSstLaudo(models.Model):
    """Gera o S-2240 de todos os trabalhadores atingidos pelo laudo.

    Alterar o laudo de um ambiente muda a condição de exposição de todo mundo
    que trabalha nele. Fazer isso trabalhador a trabalhador não escala, e é
    justamente o caso em que o evento tem de sair em massa, com a mesma data de
    início da nova condição.
    """

    _inherit = "l10n_br.sst.laudo"

    s2240_ids = fields.One2many(
        "l10n_br.esocial.s2240",
        "laudo_id",
        string="Eventos S-2240",
    )
    s2240_count = fields.Integer(
        string="S-2240",
        compute="_compute_s2240_count",
    )

    @api.depends("s2240_ids")
    def _compute_s2240_count(self):
        for rec in self:
            rec.s2240_count = len(rec.s2240_ids)

    def _contratos_afetados(self, data=None):
        """Contratos abertos nos ambientes cobertos por este laudo."""
        self.ensure_one()
        return self.env["hr.contract"].search(
            [
                ("state", "=", "open"),
                ("l10n_br_sst_ambiente_id", "in", self.ambiente_ids.ids),
            ]
        )

    def action_gerar_s2240(self):
        """Gera o S-2240 de cada trabalhador afetado pelo laudo."""
        self.ensure_one()
        if self.state != "vigente":
            raise UserError(
                _(
                    "Laudo %(nome)s: coloque o laudo em vigor antes de gerar "
                    "os eventos S-2240."
                )
                % {"nome": self.name}
            )
        contratos = self._contratos_afetados()
        if not contratos:
            raise UserError(
                _(
                    "Laudo %(nome)s: nenhum contrato aberto está vinculado aos "
                    "ambientes deste laudo."
                )
                % {"nome": self.name}
            )
        criados = self.env["l10n_br.esocial.s2240"].gerar_em_massa(
            contratos, data=self.date_from, laudo=self
        )
        return {
            "name": _("Eventos S-2240"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.esocial.s2240",
            "view_mode": "tree,form",
            "domain": [("id", "in", criados.ids)],
        }

    def action_view_s2240(self):
        self.ensure_one()
        return {
            "name": _("Eventos S-2240"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.esocial.s2240",
            "view_mode": "tree,form",
            "domain": [("laudo_id", "=", self.id)],
        }
