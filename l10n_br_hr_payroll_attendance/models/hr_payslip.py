# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import types

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Holerite alimentado pela apuração de jornada.

    Antes deste módulo, horas extras, horas noturnas e faltas eram digitadas à
    mão no holerite: a folha não enxergava a jornada. Aqui os quatro campos
    passam a ser calculados a partir da apuração, mas continuam editáveis
    (``readonly=False``) - sobrescrever é legítimo, desde que seja um ato
    consciente e não o único caminho possível.
    """

    _inherit = "hr.payslip"

    l10n_br_apuracao_dia_ids = fields.Many2many(
        comodel_name="l10n_br.hr.apuracao.dia",
        string="Dias apurados",
        compute="_compute_l10n_br_apuracao",
        help="Apurações de jornada que sustentam os números deste holerite.",
    )
    l10n_br_apuracao_count = fields.Integer(
        string="Dias com apuração",
        compute="_compute_l10n_br_apuracao",
    )
    l10n_br_tem_apuracao = fields.Boolean(
        compute="_compute_l10n_br_apuracao",
        string="Tem apuração de jornada",
    )
    l10n_br_apuracao_fechada = fields.Boolean(
        compute="_compute_l10n_br_apuracao",
        string="Apuração fechada",
        help="Verdadeiro quando toda a jornada do período está em competência "
        "fechada - é o estado em que a folha pode confiar nos números.",
    )
    l10n_br_intervalo_suprimido = fields.Float(
        string="Intervalo suprimido (h)",
        digits=(8, 4),
        compute="_compute_l10n_br_jornada",
        readonly=False,
        store=True,
        help="Período de intervalo intrajornada suprimido, pago com 50% e de "
        "natureza indenizatória (art. 71, § 4º da CLT).",
    )
    l10n_br_semanas_com_falta = fields.Integer(
        string="Semanas com falta",
        compute="_compute_l10n_br_jornada",
        readonly=False,
        store=True,
        help="Semanas atingidas por falta injustificada, base do desconto do "
        "DSR (Lei 605/49, art. 6º).",
    )
    l10n_br_justificativa_divergencia = fields.Char(
        string="Justificativa da divergência",
        help="Motivo para o holerite divergir da apuração fechada. Exigida "
        "quando a empresa bloqueia holerite divergente.",
    )

    def _l10n_br_dominio_apuracao(self):
        self.ensure_one()
        return [
            ("employee_id", "=", self.employee_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]

    @api.depends("employee_id", "date_from", "date_to")
    def _compute_l10n_br_apuracao(self):
        for slip in self:
            dias = self.env["l10n_br.hr.apuracao.dia"]
            if slip.employee_id and slip.date_from and slip.date_to:
                dias = dias.search(slip._l10n_br_dominio_apuracao())
            slip.l10n_br_apuracao_dia_ids = dias
            slip.l10n_br_apuracao_count = len(dias)
            slip.l10n_br_tem_apuracao = bool(dias)
            slip.l10n_br_apuracao_fechada = bool(dias) and all(
                dia.state == "fechado" for dia in dias
            )

    @api.depends("l10n_br_apuracao_dia_ids")
    def _compute_l10n_br_jornada(self):
        """Deriva os números de jornada da apuração (RP-16, RP-18).

        Sem apuração no período, os valores existentes são preservados: quem
        ainda digita à mão continua digitando, e a migração para o ponto
        eletrônico não zera holerite nenhum.
        """
        for slip in self:
            dias = slip.l10n_br_apuracao_dia_ids
            if not dias:
                slip.l10n_br_intervalo_suprimido = (
                    slip.l10n_br_intervalo_suprimido or 0.0
                )
                slip.l10n_br_semanas_com_falta = slip.l10n_br_semanas_com_falta or 0
                continue
            totais = slip._l10n_br_totais_apuracao(dias)
            slip.l10n_br_intervalo_suprimido = totais["intervalo_suprimido"]
            slip.l10n_br_semanas_com_falta = totais["semanas_com_falta"]

    @api.model
    def _l10n_br_totais_apuracao(self, dias):
        """Consolida a apuração do período em totais para a folha.

        O DSR sobre horas extras usa a proporção legal (HE / dias úteis x dias
        de repouso), calculada com o calendário do próprio período - não com o
        mês comercial de 30 dias, que distorceria meses com feriado.
        """
        from odoo.addons.l10n_br_hr_attendance_apuracao.models import regras_jornada

        dias_uteis = len(
            dias.filtered(lambda dia: dia.jornada_prevista and not dia.feriado)
        )
        dias_repouso = len(
            dias.filtered(lambda dia: not dia.jornada_prevista or dia.feriado)
        )
        horas_extras = sum(dias.mapped("horas_extras"))
        datas_falta = dias.filtered("falta_injustificada").mapped("date")
        return {
            "he_50": sum(dias.mapped("he_50")),
            "he_100": sum(dias.mapped("he_100")),
            "noturno": sum(dias.mapped("noturno")),
            "noturno_computado": sum(dias.mapped("noturno_computado")),
            "faltas": len(datas_falta),
            "semanas_com_falta": regras_jornada.semanas_com_falta(datas_falta),
            "intervalo_suprimido": sum(dias.mapped("intrajornada_suprimida")),
            "dsr_horas_extras": regras_jornada.dsr_sobre_horas_extras(
                horas_extras, dias_uteis, dias_repouso
            ),
            "dias_uteis": dias_uteis,
            "dias_repouso": dias_repouso,
            "atraso": sum(dias.mapped("atraso")),
        }

    def _l10n_br_preencher_horas_da_apuracao(self):
        """Preenche os campos que antes eram digitados à mão (RP-16).

        Roda no ``compute_sheet`` em vez de ser um ``compute`` de campo: os
        quatro campos são do ``l10n_br_hr_payroll`` e continuam livres para
        digitação: sobrescrevê-los em cada gravação tiraria do usuário a
        possibilidade de ajustar um caso concreto.
        """
        for slip in self:
            dias = slip.l10n_br_apuracao_dia_ids
            if not dias:
                continue
            totais = slip._l10n_br_totais_apuracao(dias)
            slip.l10n_br_horas_extras_50 = totais["he_50"]
            slip.l10n_br_horas_extras_100 = totais["he_100"]
            slip.l10n_br_horas_noturnas = totais["noturno"]
            slip.l10n_br_faltas_injustificadas = totais["faltas"]

    # ------------------------------------------------------------------
    # Dias trabalhados
    # ------------------------------------------------------------------

    def get_worked_day_lines(self, contracts, date_from, date_to):
        """Deriva os dias trabalhados da presença efetiva (RP-17).

        Quando existe apuração no período, as linhas saem dela: dias com
        trabalho, faltas e horas realmente cumpridas. Sem apuração, cai no
        comportamento do OCA ``payroll`` (calendário do contrato), o que
        mantém compatível quem ainda não usa ponto eletrônico.
        """
        self.ensure_one()
        dias = self.l10n_br_apuracao_dia_ids
        if not dias:
            return super().get_worked_day_lines(contracts, date_from, date_to)

        linhas = []
        for contrato in contracts:
            do_contrato = dias.filtered(
                lambda dia: dia.employee_id == contrato.employee_id
            )
            if not do_contrato:
                continue
            trabalhados = do_contrato.filtered(lambda dia: dia.jornada_realizada > 0)
            linhas.append(
                {
                    "name": _("Dias trabalhados (apuração de ponto)"),
                    "sequence": 1,
                    "code": "WORK100",
                    "number_of_days": len(trabalhados),
                    "number_of_hours": sum(trabalhados.mapped("jornada_realizada")),
                    "contract_id": contrato.id,
                }
            )
            faltas = do_contrato.filtered("falta_injustificada")
            if faltas:
                linhas.append(
                    {
                        "name": _("Faltas injustificadas"),
                        "sequence": 90,
                        "code": "FALTAS",
                        "number_of_days": len(faltas),
                        "number_of_hours": sum(faltas.mapped("jornada_prevista")),
                        "contract_id": contrato.id,
                    }
                )
            abonadas = do_contrato.filtered(
                lambda dia: dia.falta and not dia.falta_injustificada
            )
            if abonadas:
                linhas.append(
                    {
                        "name": _("Ausências abonadas"),
                        "sequence": 91,
                        "code": "AUSENCIA_ABONADA",
                        "number_of_days": len(abonadas),
                        "number_of_hours": sum(abonadas.mapped("jornada_prevista")),
                        "contract_id": contrato.id,
                    }
                )
        return linhas

    # ------------------------------------------------------------------
    # Regras salariais
    # ------------------------------------------------------------------

    def _get_tools_dict(self):
        """Publica os totais da apuração no ``localdict`` das regras.

        As regras passam a chamar ``tools.ponto.he_50`` etc. sem conhecer o
        modelo de apuração - se um dia a origem da jornada mudar, as regras
        salariais não mudam junto.
        """
        tools = super()._get_tools_dict()
        dias = self.l10n_br_apuracao_dia_ids
        totais = (
            self._l10n_br_totais_apuracao(dias)
            if dias
            else {
                "he_50": 0.0,
                "he_100": 0.0,
                "noturno": 0.0,
                "noturno_computado": 0.0,
                "faltas": 0,
                "semanas_com_falta": 0,
                "intervalo_suprimido": 0.0,
                "dsr_horas_extras": 0.0,
                "dias_uteis": 0,
                "dias_repouso": 0,
                "atraso": 0.0,
            }
        )
        tools["ponto"] = types.SimpleNamespace(**totais)
        return tools

    def compute_sheet(self):
        """Recalcula os campos de jornada antes de rodar as regras."""
        self._l10n_br_preencher_horas_da_apuracao()
        return super().compute_sheet()

    # ------------------------------------------------------------------
    # Divergência
    # ------------------------------------------------------------------

    def _l10n_br_divergencias(self):
        """Diferenças entre o holerite e a apuração fechada (RP-19)."""
        self.ensure_one()
        dias = self.l10n_br_apuracao_dia_ids
        if not dias:
            return []
        totais = self._l10n_br_totais_apuracao(dias)
        comparacoes = (
            (_("Horas extras 50%"), self.l10n_br_horas_extras_50, totais["he_50"]),
            (_("Horas extras 100%"), self.l10n_br_horas_extras_100, totais["he_100"]),
            (_("Horas noturnas"), self.l10n_br_horas_noturnas, totais["noturno"]),
            (
                _("Faltas injustificadas"),
                self.l10n_br_faltas_injustificadas,
                totais["faltas"],
            ),
        )
        return [
            _("%(campo)s: holerite %(holerite)s, apuração %(apuracao)s.")
            % {"campo": campo, "holerite": no_holerite, "apuracao": apurado}
            for campo, no_holerite, apurado in comparacoes
            if abs(float(no_holerite) - float(apurado)) > 0.01
        ]

    def action_payslip_done(self):
        """Bloqueia validar holerite que contraria a apuração fechada."""
        for slip in self:
            if not slip.company_id.l10n_br_bloqueia_holerite_divergente:
                continue
            if not slip.l10n_br_apuracao_fechada:
                continue
            divergencias = slip._l10n_br_divergencias()
            if divergencias and not slip.l10n_br_justificativa_divergencia:
                raise UserError(
                    _(
                        "O holerite de %(nome)s diverge da apuração de ponto "
                        "fechada:\n%(lista)s\n\nCorrija os valores ou registre "
                        "a justificativa da divergência."
                    )
                    % {
                        "nome": slip.employee_id.name,
                        "lista": "\n".join("- " + d for d in divergencias),
                    }
                )
            if divergencias:
                slip.message_post(
                    body=_(
                        "Holerite validado com divergência justificada "
                        "(%(motivo)s):\n%(lista)s"
                    )
                    % {
                        "motivo": slip.l10n_br_justificativa_divergencia,
                        "lista": "\n".join(divergencias),
                    }
                )
        return super().action_payslip_done()

    def action_ver_apuracao(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Apuração de jornada"),
            "res_model": "l10n_br.hr.apuracao.dia",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.l10n_br_apuracao_dia_ids.ids)],
        }
