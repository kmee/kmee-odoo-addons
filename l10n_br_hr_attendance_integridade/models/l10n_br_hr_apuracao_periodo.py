# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class L10nBrHrApuracaoPeriodo(models.Model):
    """Carimba a integridade do PTRP no momento em que o AEJ é gerado.

    A prova precisa acompanhar o artefato: meses depois, o que responde "qual
    programa gerou este arquivo" é o resumo gravado junto dele, não a versão
    que estiver instalada no dia da fiscalização.
    """

    _inherit = "l10n_br.hr.apuracao.periodo"

    ptrp_resumo = fields.Char(
        string="Resumo do PTRP",
        readonly=True,
        copy=False,
        help="Resumo digital do escopo atestado vigente quando o AEJ foi " "gerado.",
    )
    ptrp_integridade_ok = fields.Selection(
        selection=[
            ("confere", "Confere com o homologado"),
            ("diverge", "Diverge do homologado"),
            ("nao_configurado", "Sem resumo homologado configurado"),
        ],
        string="Integridade do PTRP",
        readonly=True,
        copy=False,
    )
    ptrp_diagnostico = fields.Text(
        string="Diagnóstico da integridade",
        readonly=True,
        copy=False,
    )

    def action_gerar_aej(self):
        resultado = super().action_gerar_aej()
        verificador = self.env["l10n_br.hr.ptrp.integridade"]
        estado = verificador.verificar()
        diagnostico = verificador.texto_do_diagnostico()
        situacao = (
            "nao_configurado"
            if estado["confere"] is None
            else ("confere" if estado["confere"] else "diverge")
        )
        for periodo in self:
            periodo.write(
                {
                    "ptrp_resumo": estado["resumo"],
                    "ptrp_integridade_ok": situacao,
                    "ptrp_diagnostico": diagnostico,
                }
            )
            if situacao != "confere" or estado["divergencias"]:
                periodo.message_post(body=diagnostico.replace("\n", "<br/>"))
        return resultado

    def action_ver_integridade(self):
        self.ensure_one()
        diagnostico = self.env["l10n_br.hr.ptrp.integridade"].texto_do_diagnostico()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Integridade do PTRP"),
                "message": diagnostico,
                "sticky": True,
            },
        }
