# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models

from ..models import afd_layout


class L10nBrHrAfdExportWizard(models.TransientModel):
    """Gera o AFD de um período para entrega ao Auditor-Fiscal (art. 85)."""

    _name = "l10n_br.hr.afd.export.wizard"
    _description = "Exportação de AFD"

    rep_id = fields.Many2one(
        comodel_name="l10n_br.hr.rep",
        string="REP",
        required=True,
    )
    date_from = fields.Date(string="De", required=True)
    date_to = fields.Date(string="Até", required=True)
    fuso_horas = fields.Float(
        string="Fuso do estabelecimento",
        default=-3.0,
        help="Fuso gravado nos campos de data e hora do arquivo.",
    )
    arquivo = fields.Binary(string="AFD gerado", readonly=True, attachment=False)
    arquivo_nome = fields.Char(readonly=True)

    def action_gerar(self):
        self.ensure_one()
        nome, conteudo = self.rep_id.gerar_afd(
            self.date_from, self.date_to, fuso_horas=self.fuso_horas
        )
        self.write(
            {
                "arquivo_nome": nome,
                "arquivo": base64.b64encode(
                    conteudo.encode(afd_layout.ENCODING_AFD, errors="replace")
                ),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
