# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Tipos de rescisão que dão direito a aviso prévio indenizado pago pelo
# empregador e à multa do FGTS (com percentuais distintos, ver as regras).
L10N_BR_TIPOS_RESCISAO_COM_AVISO_E_MULTA = ("sem_justa_causa", "acordo")


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_br_abono_pecuniario = fields.Boolean(
        string="Abono Pecuniário",
        help="Venda de 1/3 dos dias de férias (CLT art. 143). Caminho "
        "LEGADO, sem alocação vinculada: presume período de 30 dias de "
        "direito e vende 10. Para respeitar os dias de direito reais "
        "(CLT art. 130) e o fracionamento, vincule "
        "l10n_br_ferias_allocation_id e use l10n_br_dias_abono.",
    )
    l10n_br_ferias_allocation_id = fields.Many2one(
        comodel_name="hr.leave.allocation",
        string="Período Aquisitivo (Férias)",
        domain="[('employee_id', '=', employee_id)]",
        help="Alocação de férias (período aquisitivo, CLT art. 130) cujo "
        "direito está sendo pago neste holerite. Define os dias de "
        "direito (30/24/18/12/0 conforme as faltas injustificadas) e "
        "permite o fracionamento em até 3 períodos (CLT art. 134 §1º, "
        "Lei 13.467/2017): cada holerite de férias paga os dias DESTE "
        "período/fração gozado, não o saldo inteiro da alocação.",
    )
    l10n_br_dias_direito_ferias = fields.Float(
        string="Dias de Direito (Período Aquisitivo)",
        compute="_compute_dias_direito_ferias",
        help="Dias de férias a que o empregado tem direito no período "
        "aquisitivo vinculado, conforme as faltas injustificadas "
        "(CLT art. 130): 30/24/18/12/0 dias. Informativo.",
    )
    l10n_br_dias_periodo_gozado = fields.Integer(
        string="Dias Gozados neste Período",
        help="Dias corridos efetivamente GOZADOS neste holerite — uma das "
        "até 3 frações do período aquisitivo vinculado (CLT art. 134 §1º). "
        "Só tem efeito quando l10n_br_ferias_allocation_id está definido; "
        "sem alocação, usa-se o caminho legado (l10n_br_abono_pecuniario).",
    )
    l10n_br_dias_abono = fields.Integer(
        string="Dias de Abono Pecuniário (Venda)",
        help="Dias vendidos como abono pecuniário NESTE holerite (CLT art. "
        "143), até 1/3 dos dias de direito do período aquisitivo vinculado. "
        "O abono é indivisível (CLT art. 143 §2º): só pode ser lançado em "
        "UMA das frações. Só tem efeito com l10n_br_ferias_allocation_id "
        "definido; sem alocação, usa-se l10n_br_abono_pecuniario (legado).",
    )
    l10n_br_dias_ferias_gozadas = fields.Integer(
        string="Dias de Férias Gozadas",
        compute="_compute_dias_ferias_gozadas",
    )
    l10n_br_avos_13 = fields.Integer(
        string="Avos de 13º",
        compute="_compute_avos_13",
    )
    l10n_br_avos_ferias = fields.Integer(
        string="Avos de Férias Proporcionais",
        compute="_compute_avos_ferias",
        help="Meses (fração >= 15 dias) do período aquisitivo em curso, "
        "usados para as férias proporcionais na rescisão. Quando o aviso "
        "prévio é INDENIZADO (rescisão sem justa causa ou acordo), o "
        "contrato é projetado pelos dias de aviso para este cômputo "
        "(Súmula 371 TST).",
    )
    l10n_br_primeira_parcela_13_paga = fields.Float(
        string="1ª Parcela do 13º já paga",
        help="Valor da 1ª parcela do 13º já paga (para cálculo da 2ª parcela)",
    )
    l10n_br_liquido_13 = fields.Float(
        string="Líquido 13º",
        compute="_compute_liquido_13",
    )

    # ══════════════════════════════════════════════════════════════════
    # RESCISÃO (RF-06)
    # ══════════════════════════════════════════════════════════════════
    l10n_br_tipo_rescisao = fields.Selection(
        selection=[
            ("sem_justa_causa", "Sem Justa Causa (Iniciativa do Empregador)"),
            ("pedido_demissao", "Pedido de Demissão"),
            ("justa_causa", "Justa Causa (CLT art. 482)"),
            ("acordo", "Comum Acordo (CLT art. 484-A)"),
        ],
        string="Tipo de Rescisão",
        help="Determina quais verbas são devidas: aviso prévio indenizado "
        "e multa do FGTS somente em 'sem justa causa' (100%/40%) e "
        "'acordo' (CLT art. 484-A, I, 'a' e 'b': 50%/20%); férias "
        "proporcionais excluídas na justa causa (Súmula 171 TST; CLT art. "
        "146 parágrafo único e art. 147); 13º proporcional excluído "
        "SOMENTE na justa causa (Lei 4.090/62 art. 3º; Decreto 57.155/65 "
        "art. 7º) — devido inclusive no pedido de demissão (Súmula 157 "
        "TST); férias vencidas devidas em qualquer hipótese (CLT art. 146, "
        "caput).",
    )
    l10n_br_aviso_previo = fields.Selection(
        selection=[
            ("indenizado", "Indenizado"),
            ("trabalhado", "Trabalhado"),
            ("nao_aplicavel", "Não Aplicável"),
        ],
        string="Aviso Prévio",
        help="INDENIZADO: gera a verba AVISO_PREVIO_INDENIZADO e projeta o "
        "contrato para o 13º e as férias proporcionais (Súmula 371 TST). "
        "TRABALHADO: já remunerado pela folha mensal do próprio período; "
        "esta rescisão não gera verba adicional (date_to já reflete o fim "
        "do aviso trabalhado). NÃO APLICÁVEL: justa causa ou pedido de "
        "demissão sem aviso indenizado pelo empregador.",
    )
    l10n_br_fgts_saldo_conta = fields.Float(
        string="Saldo FGTS na Conta Vinculada",
        help="Base da multa de 40% (ou 20% no acordo) do FGTS (Lei "
        "8.036/90 art. 18 §1º; CLT art. 484-A, I, 'b'): "
        "total depositado na conta vinculada durante o contrato, conforme "
        "o extrato oficial (FGTS Digital). Quando deixado em branco (0), a "
        "regra usa o FALLBACK 8% × salário × meses trabalhados — uma "
        "ESTIMATIVA sem juros/correção monetária, que subestima o saldo "
        "real; preencher com o extrato sempre que disponível.",
    )

    @api.depends("l10n_br_ferias_allocation_id.number_of_days")
    def _compute_dias_direito_ferias(self):
        for rec in self:
            rec.l10n_br_dias_direito_ferias = (
                rec.l10n_br_ferias_allocation_id.number_of_days
                if rec.l10n_br_ferias_allocation_id
                else 0.0
            )

    @api.depends(
        "l10n_br_ferias_allocation_id",
        "l10n_br_dias_periodo_gozado",
        "l10n_br_abono_pecuniario",
    )
    def _compute_dias_ferias_gozadas(self):
        for rec in self:
            if rec.l10n_br_ferias_allocation_id:
                # RF-19: dias GOZADOS nesta fração do período aquisitivo
                # (fracionamento em até 3 períodos, CLT art. 134 §1º).
                rec.l10n_br_dias_ferias_gozadas = rec.l10n_br_dias_periodo_gozado
            elif rec.l10n_br_abono_pecuniario:
                # Caminho LEGADO (sem alocação): 30 dias de direito
                # presumidos, vende 10 (1/3), goza 20.
                rec.l10n_br_dias_ferias_gozadas = 20
            else:
                rec.l10n_br_dias_ferias_gozadas = 30

    @api.depends(
        "l10n_br_ferias_allocation_id",
        "l10n_br_dias_abono",
        "l10n_br_abono_pecuniario",
        "l10n_br_dias_ferias_gozadas",
    )
    def _compute_dias_ferias_vendidas(self):
        for rec in self:
            if rec.l10n_br_ferias_allocation_id:
                rec.l10n_br_dias_ferias_vendidas = rec.l10n_br_dias_abono
            elif rec.l10n_br_abono_pecuniario:
                rec.l10n_br_dias_ferias_vendidas = 30 - rec.l10n_br_dias_ferias_gozadas
            else:
                rec.l10n_br_dias_ferias_vendidas = 0

    l10n_br_dias_ferias_vendidas = fields.Integer(
        string="Dias de Férias Vendidas",
        compute="_compute_dias_ferias_vendidas",
        help="Dias vendidos como abono pecuniário neste holerite (soma o "
        "caminho novo, com alocação, e o legado, sem alocação).",
    )

    @api.constrains(
        "l10n_br_ferias_allocation_id",
        "l10n_br_dias_periodo_gozado",
        "l10n_br_dias_abono",
    )
    def _check_fracionamento_ferias(self):
        """Valida direito, indivisibilidade do abono e fracionamento (RF-19).

        CLT art. 130: dias gozados + vendidos não pode superar o direito do
        período aquisitivo. CLT art. 143 §2º: o abono é indivisível — só uma
        fração pode vendê-lo, e o limite é 1/3 do direito (não fixo em 10
        dias). CLT art. 134 §1º (Lei 13.467/2017): até 3 períodos por
        período aquisitivo, um deles com pelo menos 14 dias corridos e os
        demais com pelo menos 5 dias corridos cada.
        """
        for rec in self:
            alloc = rec.l10n_br_ferias_allocation_id
            if not alloc:
                continue
            direito = alloc.number_of_days
            if rec.l10n_br_dias_abono > direito / 3:
                raise ValidationError(
                    _(
                        "O abono pecuniário não pode superar 1/3 dos dias de "
                        "direito do período aquisitivo (CLT art. 143): "
                        "máximo de %(maximo)s dias para %(direito)s dias de "
                        "direito."
                    )
                    % {"maximo": direito / 3, "direito": direito}
                )
            if rec.l10n_br_dias_periodo_gozado < 0 or rec.l10n_br_dias_abono < 0:
                raise ValidationError(
                    _("Os dias gozados e vendidos não podem ser negativos.")
                )
            # Irmãos: demais holerites de férias (não cancelados) da MESMA
            # alocação, formando as frações do período aquisitivo.
            irmaos = self.env["hr.payslip"].search(
                [
                    ("l10n_br_ferias_allocation_id", "=", alloc.id),
                    ("state", "!=", "cancel"),
                ]
            )
            fracoes = irmaos.filtered(lambda p: p.l10n_br_dias_periodo_gozado > 0)
            dias_fracoes = fracoes.mapped("l10n_br_dias_periodo_gozado")
            if len(fracoes) > 3:
                raise ValidationError(
                    _(
                        "As férias só podem ser fracionadas em até 3 "
                        "períodos por período aquisitivo (CLT art. 134 §1º, "
                        "Lei 13.467/2017)."
                    )
                )
            if len(fracoes) >= 2:
                if max(dias_fracoes) < 14:
                    raise ValidationError(
                        _(
                            "No fracionamento das férias, pelo menos um "
                            "período deve ter 14 dias corridos ou mais "
                            "(CLT art. 134 §1º)."
                        )
                    )
                if any(d < 5 for d in dias_fracoes):
                    raise ValidationError(
                        _(
                            "No fracionamento das férias, nenhum período "
                            "pode ter menos de 5 dias corridos "
                            "(CLT art. 134 §1º)."
                        )
                    )
            total_abono = sum(irmaos.mapped("l10n_br_dias_abono"))
            total_gozado = sum(dias_fracoes)
            if total_gozado + total_abono > direito:
                raise ValidationError(
                    _(
                        "A soma dos dias gozados e vendidos em todas as "
                        "frações deste período aquisitivo (%(total)s) supera "
                        "os %(direito)s dias de direito."
                    )
                    % {"total": total_gozado + total_abono, "direito": direito}
                )

    @api.depends(
        "contract_id", "date_to", "l10n_br_tipo_rescisao", "l10n_br_aviso_previo"
    )
    def _compute_avos_13(self):
        from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
            calc_decimo_avos,
        )

        for rec in self:
            if rec.contract_id and rec.date_to:
                referencia = rec._l10n_br_data_projetada_rescisao()
                rec.l10n_br_avos_13 = calc_decimo_avos(
                    rec.contract_id.date_start, referencia
                )
            else:
                rec.l10n_br_avos_13 = 0

    @api.depends(
        "contract_id", "date_to", "l10n_br_tipo_rescisao", "l10n_br_aviso_previo"
    )
    def _compute_avos_ferias(self):
        for rec in self:
            if rec.contract_id and rec.contract_id.date_start and rec.date_to:
                referencia = rec._l10n_br_data_projetada_rescisao()
                rec.l10n_br_avos_ferias = self._calc_avos_ferias_proporcionais(
                    rec.contract_id.date_start, referencia
                )
            else:
                rec.l10n_br_avos_ferias = 0

    @staticmethod
    def _calc_avos_ferias_proporcionais(data_admissao, data_referencia):
        """Avos de férias proporcionais do período aquisitivo em curso.

        Conta os meses (alinhados ao aniversário de admissão) com fração
        igual ou superior a 15 dias, desde o início do período aquisitivo
        em curso (último aniversário de admissão <= referência) até a data
        de referência (rescisão, já projetada pelo aviso indenizado quando
        aplicável — ver ``_l10n_br_data_projetada_rescisao``). Máximo de 12
        avos.

        Nota: NÃO considera férias vencidas de períodos aquisitivos
        completos e não gozados - ver ``_l10n_br_ferias_vencidas_dados``.
        """
        anos = data_referencia.year - data_admissao.year
        inicio = data_admissao + relativedelta(years=anos)
        if inicio > data_referencia:
            inicio = data_admissao + relativedelta(years=anos - 1)
        avos = 0
        cursor = inicio
        while cursor <= data_referencia:
            fim_mes = cursor + relativedelta(months=1) - relativedelta(days=1)
            if fim_mes <= data_referencia:
                avos += 1
            else:
                dias = (data_referencia - cursor).days + 1
                if dias >= 15:
                    avos += 1
            cursor += relativedelta(months=1)
        return min(avos, 12)

    @staticmethod
    def _l10n_br_codes_media_habitual():
        """Códigos de rubrica cuja média (RF-18) compõe férias/13º/rescisão.

        Súmula 45 TST / CLT art. 142: parcelas variáveis habituais (horas
        extras habituais, adicional noturno) integram pela MÉDIA dos
        últimos meses. Adicionais CONTRATUAIS fixos (periculosidade,
        insalubridade) são um percentual constante do salário — não variam
        mês a mês — e por isso ficam FORA desta lista; sua integração às
        apurações separadas é uma lacuna distinta (fora desta onda),
        documentada no relatório.
        """
        return ("HE_50", "HE_100", "ADICIONAL_NOTURNO")

    def _l10n_br_dias_aviso_previo(self):
        """Dias de aviso prévio devidos (Lei 12.506/2011). Ver salary_rules_br."""
        self.ensure_one()
        if not self.contract_id or not self.contract_id.date_start or not self.date_to:
            return 0
        from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
            calc_aviso_previo_dias,
        )

        return calc_aviso_previo_dias(self.contract_id.date_start, self.date_to)

    def _l10n_br_aviso_indenizado_devido(self):
        """Aviso prévio indenizado é devido pelo empregador (RF-06).

        Só em rescisão sem justa causa ou por acordo (CLT art. 484-A), e só
        quando marcado como INDENIZADO (o trabalhado já foi pago na folha
        mensal do próprio período de aviso).
        """
        self.ensure_one()
        return (
            self.l10n_br_tipo_rescisao in L10N_BR_TIPOS_RESCISAO_COM_AVISO_E_MULTA
            and self.l10n_br_aviso_previo == "indenizado"
        )

    def _l10n_br_data_projetada_rescisao(self):
        """Data de referência para 13º/férias proporcionais na rescisão.

        Súmula 371 TST: a projeção do aviso prévio indenizado é considerada
        para o 13º salário e as férias proporcionais (mas não para as
        demais verbas rescisórias). Fora da rescisão (ou sem aviso
        indenizado), a referência é o próprio ``date_to``.
        """
        self.ensure_one()
        if self.date_to and self._l10n_br_aviso_indenizado_devido():
            dias = self._l10n_br_dias_aviso_previo()
            return self.date_to + relativedelta(days=dias)
        return self.date_to

    def _l10n_br_ferias_vencidas_dados(self):
        """Períodos aquisitivos VENCIDOS e não gozados até a rescisão.

        CLT art. 146: na cessação do contrato, qualquer que seja a causa,
        são devidas as férias de período aquisitivo já COMPLETO e ainda não
        gozado ("vencidas") — diferente das proporcionais do período em
        curso (``l10n_br_avos_ferias``). CLT art. 137: pagas após o período
        concessivo (os 12 meses seguintes ao término do período aquisitivo,
        CLT art. 134), o pagamento é em DOBRO.

        "Não gozado" é apurado pelos holerites de férias CONFIRMADOS
        (state == "done") já vinculados à mesma alocação
        (``l10n_br_ferias_allocation_id``): dias de direito menos os já
        pagos (gozados + vendidos) em qualquer fração anterior.

        Returns:
            list[dict]: ``[{"dias": int, "dobro": bool}, ...]``, um item por
            período aquisitivo vencido com saldo residual.
        """
        self.ensure_one()
        if not self.employee_id or not self.date_to:
            return []
        vacation_type = self.env.ref(
            "l10n_br_hr_vacation.leave_type_ferias", raise_if_not_found=False
        )
        if not vacation_type:
            return []
        allocations = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("holiday_status_id", "=", vacation_type.id),
                ("state", "=", "validate"),
                ("date_to", "!=", False),
                ("date_to", "<=", self.date_to),
            ]
        )
        resultado = []
        for alloc in allocations:
            pagos = self.env["hr.payslip"].search(
                [
                    ("l10n_br_ferias_allocation_id", "=", alloc.id),
                    ("state", "=", "done"),
                ]
            )
            dias_pagos = sum(pagos.mapped("l10n_br_dias_periodo_gozado")) + sum(
                pagos.mapped("l10n_br_dias_abono")
            )
            restante = alloc.number_of_days - dias_pagos
            if restante > 0:
                periodo_concessivo_fim = alloc.date_to + relativedelta(years=1)
                dobro = self.date_to > periodo_concessivo_fim
                resultado.append({"dias": restante, "dobro": dobro})
        return resultado

    @api.depends("line_ids", "l10n_br_primeira_parcela_13_paga")
    def _compute_liquido_13(self):
        for rec in self:
            bruto = sum(
                rec.line_ids.filtered(
                    lambda line: line.code == "DECIMO_TERCEIRO_BRUTO"
                ).mapped("total")
            )
            inss_13 = sum(
                rec.line_ids.filtered(lambda line: line.code == "INSS_13").mapped(
                    "total"
                )
            )
            irrf_13 = sum(
                rec.line_ids.filtered(lambda line: line.code == "IRRF_13").mapped(
                    "total"
                )
            )
            rec.l10n_br_liquido_13 = (
                bruto - inss_13 - irrf_13 - rec.l10n_br_primeira_parcela_13_paga
            )

    def _get_baselocaldict(self, contracts):
        localdict = super()._get_baselocaldict(contracts)
        for code in (
            "FERIAS",
            "ADICIONAL_FERIAS",
            "ABONO_PECUNIARIO",
            "ADICIONAL_ABONO",
            "DECIMO_TERCEIRO_BRUTO",
            "ADIANTAMENTO_13",
            "INSS_13",
            "IRRF_13",
            "BASE_IRRF_13",
            # Pensão retida sobre a apuração exclusiva do 13º (RF-03): a base
            # do IRRF do 13º a referencia mesmo quando o empregado não tem
            # pensão (regra condicional que não dispara).
            "PENSAO_ALIMENTICIA_13",
            "DECIMO_RESCISAO",
            "SALDO_SALARIO",
            "FERIAS_INDENIZADAS",
            "ADICIONAL_FERIAS_INDENIZADAS",
            # RF-06: verbas rescisórias novas (aviso, multa do FGTS, férias
            # vencidas) — pré-populadas para as regras condicionais que
            # referenciam estes códigos quando a verba não é devida.
            "FERIAS_VENCIDAS",
            "ADICIONAL_FERIAS_VENCIDAS",
            "AVISO_PREVIO_INDENIZADO",
            "FGTS_AVISO",
            "MULTA_FGTS",
        ):
            localdict.setdefault(code, 0.0)
        return localdict
