# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import regras_jornada

_logger = logging.getLogger(__name__)


class L10nBrHrApuracaoDia(models.Model):
    """Apuração da jornada de um funcionário em um dia.

    É o registro que traduz marcações em jornada: pareia, aplica tolerância,
    separa trecho noturno, confere intervalo e classifica o excedente em
    faixas. Tudo o que a folha e o AEJ consomem sai daqui, e nada aqui altera
    a marcação de origem.
    """

    _name = "l10n_br.hr.apuracao.dia"
    _description = "Apuração Diária de Jornada"
    _order = "date desc, employee_id"
    _rec_name = "display_name"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Funcionário",
        required=True,
        index=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        comodel_name="hr.contract",
        string="Contrato",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    date = fields.Date(string="Dia", required=True, index=True)
    periodo_id = fields.Many2one(
        comodel_name="l10n_br.hr.apuracao.periodo",
        string="Competência",
        ondelete="cascade",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("rascunho", "Rascunho"),
            ("apurado", "Apurado"),
            ("fechado", "Fechado"),
        ],
        default="rascunho",
        required=True,
        index=True,
    )

    marcacao_ids = fields.One2many(
        comodel_name="l10n_br.hr.marcacao",
        inverse_name="apuracao_dia_id",
        string="Marcações",
    )
    attendance_ids = fields.One2many(
        comodel_name="hr.attendance",
        inverse_name="l10n_br_apuracao_dia_id",
        string="Sessões",
    )

    jornada_prevista = fields.Float(
        string="Jornada prevista (h)",
        digits=(8, 4),
        help="Duração contratual do dia, vinda do calendário de trabalho.",
    )
    jornada_realizada = fields.Float(
        string="Jornada realizada (h)",
        digits=(8, 4),
    )
    horas_extras = fields.Float(string="Horas extras (h)", digits=(8, 4))
    he_50 = fields.Float(string="HE 50% (h)", digits=(8, 4))
    he_100 = fields.Float(string="HE 100% (h)", digits=(8, 4))
    atraso = fields.Float(
        string="Atraso/saída antecipada (h)",
        digits=(8, 4),
        help="Déficit de jornada no dia, já descontada a tolerância legal.",
    )
    noturno = fields.Float(
        string="Horas noturnas (h)",
        digits=(8, 4),
        help="Tempo cronológico trabalhado entre 22h e 5h.",
    )
    noturno_computado = fields.Float(
        string="Horas noturnas computadas (h)",
        digits=(8, 4),
        help="Horas noturnas já convertidas pela hora reduzida de 52min30s.",
    )
    intrajornada_gozada = fields.Float(string="Intervalo gozado (h)", digits=(8, 4))
    intrajornada_devida = fields.Float(string="Intervalo devido (h)", digits=(8, 4))
    intrajornada_suprimida = fields.Float(
        string="Intervalo suprimido (h)",
        digits=(8, 4),
        help="Período suprimido do intervalo, indenizável com 50% "
        "(art. 71, § 4º da CLT).",
    )
    banco_horas_delta = fields.Float(
        string="Banco de horas (h)",
        digits=(8, 4),
        help="Saldo do dia quando a compensação está ativa: positivo credita, "
        "negativo debita.",
    )

    feriado = fields.Boolean()
    dia_semana = fields.Selection(
        selection=[
            ("0", "Segunda"),
            ("1", "Terça"),
            ("2", "Quarta"),
            ("3", "Quinta"),
            ("4", "Sexta"),
            ("5", "Sábado"),
            ("6", "Domingo"),
        ],
        compute="_compute_dia_semana",
        store=True,
    )
    paridade_ok = fields.Boolean(
        string="Marcações pareadas",
        default=True,
        help="Falso quando sobra marcação sem par - o dia tem número ímpar de "
        "registros e precisa de tratamento antes do fechamento.",
    )
    interjornada_ok = fields.Boolean(
        string="Interjornada de 11h respeitada",
        default=True,
        help="Art. 66 da CLT.",
    )
    ocorrencia_ids = fields.Many2many(
        comodel_name="l10n_br.hr.ocorrencia",
        string="Ocorrências",
    )
    falta = fields.Boolean(
        help="Dia útil sem marcação e sem ocorrência que abone.",
    )
    falta_injustificada = fields.Boolean(
        string="Falta injustificada",
        help="Falta sem ocorrência que abone: desconta o dia e o DSR.",
    )
    inconsistencia = fields.Text(
        string="Inconsistências",
        help="O que impede considerar a apuração deste dia confiável.",
    )
    display_name = fields.Char(compute="_compute_display_name_apuracao")

    _sql_constraints = [
        (
            "employee_date_uniq",
            "unique(employee_id, date)",
            "Já existe apuração deste funcionário para este dia.",
        ),
    ]

    @api.depends("date")
    def _compute_dia_semana(self):
        for rec in self:
            rec.dia_semana = str(rec.date.weekday()) if rec.date else False

    @api.depends("employee_id", "date")
    def _compute_display_name_apuracao(self):
        for rec in self:
            rec.display_name = "%s - %s" % (
                rec.employee_id.name or "",
                fields.Date.to_string(rec.date) or "",
            )

    # ------------------------------------------------------------------
    # Jornada contratual
    # ------------------------------------------------------------------

    def _fuso(self):
        self.ensure_one()
        return pytz.timezone(
            self.employee_id.tz
            or self.contract_id.resource_calendar_id.tz
            or "America/Sao_Paulo"
        )

    def _limites_do_dia(self):
        """Início e fim do dia em UTC naive, no fuso do funcionário."""
        self.ensure_one()
        fuso = self._fuso()
        inicio_local = fuso.localize(datetime.combine(self.date, time.min))
        fim_local = fuso.localize(datetime.combine(self.date, time.max))
        return (
            inicio_local.astimezone(pytz.utc).replace(tzinfo=None),
            fim_local.astimezone(pytz.utc).replace(tzinfo=None),
        )

    def _intervalos_previstos(self):
        """Faixas de horário previstas no calendário para este dia.

        Returns:
            Lista de ``(inicio, fim)`` em UTC naive. Vazia em dia sem jornada
            prevista (folga, feriado ou calendário sem linha para o dia).
        """
        self.ensure_one()
        calendario = self.contract_id.resource_calendar_id
        if not calendario or not self.date:
            return []
        fuso = self._fuso()
        dia_semana = str(self.date.weekday())
        linhas = calendario.attendance_ids.filtered(
            lambda linha: linha.dayofweek == dia_semana
            and (not linha.date_from or linha.date_from <= self.date)
            and (not linha.date_to or linha.date_to >= self.date)
        )
        intervalos = []
        for linha in linhas:
            inicio = fuso.localize(
                datetime.combine(self.date, time.min) + timedelta(hours=linha.hour_from)
            )
            fim = fuso.localize(
                datetime.combine(self.date, time.min) + timedelta(hours=linha.hour_to)
            )
            intervalos.append(
                (
                    inicio.astimezone(pytz.utc).replace(tzinfo=None),
                    fim.astimezone(pytz.utc).replace(tzinfo=None),
                )
            )
        return sorted(intervalos)

    def _horas_previstas(self):
        """Duração contratual do dia, em horas."""
        self.ensure_one()
        return sum(
            (fim - inicio).total_seconds() / 3600.0
            for inicio, fim in self._intervalos_previstos()
        )

    def _codigo_horario_contratual(self):
        """Código do horário contratual para o registro 04 do AEJ.

        Identifica o padrão de jornada do dia (não o calendário inteiro), que
        é o que o AEJ pede: dias com escalas diferentes têm códigos
        diferentes.
        """
        self.ensure_one()
        intervalos = self._intervalos_previstos()
        if not intervalos:
            return ""
        fuso = self._fuso()
        partes = []
        for inicio, fim in intervalos:
            inicio_local = pytz.utc.localize(inicio).astimezone(fuso)
            fim_local = pytz.utc.localize(fim).astimezone(fuso)
            partes.append(inicio_local.strftime("%H%M"))
            partes.append(fim_local.strftime("%H%M"))
        return "H" + "".join(partes)

    # ------------------------------------------------------------------
    # Apuração
    # ------------------------------------------------------------------

    def _e_feriado(self):
        self.ensure_one()
        if "hr.holidays.public" not in self.env:
            return False
        return self.env["hr.holidays.public"].is_public_holiday(
            selected_date=self.date, employee_id=self.employee_id.id
        )

    def _parametros(self):
        """Parâmetros de apuração aplicáveis, com a empresa como padrão."""
        self.ensure_one()
        empresa = self.company_id or self.env.company
        return {
            "tolerancia_diaria": empresa.l10n_br_tolerancia_diaria
            or regras_jornada.TOLERANCIA_DIARIA,
            "tolerancia_marcacao": empresa.l10n_br_tolerancia_marcacao
            or regras_jornada.TOLERANCIA_POR_MARCACAO,
            "intrajornada_minima": empresa.l10n_br_intrajornada_minima,
        }

    def _marcacoes_validas(self):
        """Marcações do dia que entram na apuração, em ordem cronológica.

        Desconsideradas ficam de fora do cálculo mas continuam vinculadas ao
        dia - o espelho de ponto precisa mostrá-las com o motivo.
        """
        self.ensure_one()
        return self.marcacao_ids.filtered(lambda m: m.state != "desconsiderada").sorted(
            "datetime_marcacao"
        )

    def apurar(self):
        """Recalcula a apuração dos dias selecionados (RP-09 a RP-14)."""
        for dia in self:
            if dia.state == "fechado":
                raise UserError(
                    _(
                        "A competência de %(nome)s em %(dia)s está fechada. "
                        "Reabra a competência para reapurar."
                    )
                    % {
                        "nome": dia.employee_id.name,
                        "dia": fields.Date.to_string(dia.date),
                    }
                )
            dia._apurar_um()
        return True

    def _apurar_um(self):
        self.ensure_one()
        parametros = self._parametros()
        marcacoes = self._marcacoes_validas()
        momentos = marcacoes.mapped("datetime_marcacao")
        pares, impar = regras_jornada.parear_marcacoes(momentos)
        inconsistencias = []

        realizados = regras_jornada.minutos_trabalhados(pares)
        previstos = self._horas_previstas() * 60.0
        feriado = self._e_feriado()

        extra, deficit = self._aplica_tolerancia(previstos, realizados, parametros)

        gozado = regras_jornada.minutos_intervalo(pares)
        devido = regras_jornada.intrajornada_minima(
            realizados, parametros["intrajornada_minima"]
        )
        suprimido = regras_jornada.intrajornada_suprimida(
            realizados, gozado, parametros["intrajornada_minima"]
        )

        # O adicional noturno é a única regra sensível ao fuso: a janela das
        # 22h às 5h é horário local, e o ORM guarda tudo em UTC.
        noturno = regras_jornada.minutos_noturnos(self._pares_locais(pares))
        faixas = self._faixas_horas_extras(feriado)
        distribuicao = regras_jornada.classifica_horas_extras(extra, faixas)

        if impar:
            inconsistencias.append(
                _("Marcação sem par às %s: o dia tem número ímpar de registros.")
                % fields.Datetime.to_string(impar)
            )
        if suprimido:
            inconsistencias.append(
                _("Intervalo intrajornada suprimido em %d minutos.") % suprimido
            )
        interjornada_ok = self._confere_interjornada(pares)
        if not interjornada_ok:
            inconsistencias.append(
                _("Interjornada inferior a 11 horas (art. 66 da CLT).")
            )

        sem_marcacao = not pares and not impar
        abonado = any(self.ocorrencia_ids.mapped("abona"))
        # Falta é o dia com jornada prevista e sem trabalho; se há ocorrência
        # que abone (atestado, férias, folga), continua sendo falta - só não é
        # injustificada, e é essa distinção que a folha e o AEJ consomem.
        falta = bool(sem_marcacao and previstos)

        self.write(
            {
                "jornada_prevista": previstos / 60.0,
                "jornada_realizada": realizados / 60.0,
                "horas_extras": extra / 60.0,
                "he_50": self._soma_faixa(distribuicao, 1.5) / 60.0,
                "he_100": self._soma_faixa(distribuicao, 2.0) / 60.0,
                "atraso": deficit / 60.0,
                "noturno": noturno / 60.0,
                "noturno_computado": regras_jornada.horas_noturnas_computadas(
                    noturno, self._usa_hora_reduzida()
                ),
                "intrajornada_gozada": gozado / 60.0,
                "intrajornada_devida": devido / 60.0,
                "intrajornada_suprimida": suprimido / 60.0,
                "feriado": feriado,
                "paridade_ok": not impar,
                "interjornada_ok": interjornada_ok,
                "falta": falta,
                "falta_injustificada": falta and not abonado,
                "inconsistencia": "\n".join(inconsistencias),
                "state": "apurado",
            }
        )
        self._sincronizar_sessoes(pares)

    def _aplica_tolerancia(self, previstos, realizados, parametros):
        """Tolerância diária configurada (padrão legal de 10 minutos)."""
        self.ensure_one()
        return regras_jornada.aplica_tolerancia(
            previstos, realizados, parametros["tolerancia_diaria"]
        )

    def _para_local(self, momento):
        """Converte datetime UTC naive para o fuso do funcionário, naive."""
        self.ensure_one()
        return pytz.utc.localize(momento).astimezone(self._fuso()).replace(tzinfo=None)

    def _pares_locais(self, pares):
        return [
            (self._para_local(entrada), self._para_local(saida))
            for entrada, saida in pares
        ]

    def _usa_hora_reduzida(self):
        """Hora noturna reduzida vale para o trabalhador urbano (art. 73)."""
        return True

    def _faixas_horas_extras(self, feriado):
        """Faixas aplicáveis ao dia.

        Domingo e feriado vão a 100% desde a primeira hora; dia útil segue a
        regra geral de 50%. Convenção coletiva que fixe outra escada entra
        pelo cadastro de faixas do módulo de multiplicador, quando instalado.
        """
        self.ensure_one()
        if feriado or self.date.weekday() == 6:
            return [{"limite_minutos": None, "multiplicador": 2.0}]
        return [{"limite_minutos": None, "multiplicador": 1.5}]

    @staticmethod
    def _soma_faixa(distribuicao, multiplicador):
        return sum(
            minutos
            for minutos, fator in distribuicao
            if abs(fator - multiplicador) < 0.001
        )

    def _confere_interjornada(self, pares):
        """Compara a primeira entrada do dia com a última saída anterior."""
        self.ensure_one()
        if not pares:
            return True
        anterior = self.search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("date", "<", self.date),
            ],
            order="date desc",
            limit=1,
        )
        if not anterior:
            return True
        ultima_saida = max(
            anterior._marcacoes_validas().mapped("datetime_marcacao"),
            default=None,
        )
        return regras_jornada.interjornada_respeitada(ultima_saida, pares[0][0])

    def _sincronizar_sessoes(self, pares):
        """Materializa os pares como ``hr.attendance``.

        O Odoo (e os módulos de hora extra que já existem) enxerga jornada
        através do ``hr.attendance``; refazer as sessões a cada apuração
        mantém as duas visões coerentes sem duplicar a fonte da verdade, que
        continua sendo a marcação.
        """
        self.ensure_one()
        self.attendance_ids.unlink()
        marcacoes = self._marcacoes_validas()
        por_momento = {m.datetime_marcacao: m for m in marcacoes}
        for indice, (entrada, saida) in enumerate(pares, start=1):
            sessao = self.env["hr.attendance"].create(
                {
                    "employee_id": self.employee_id.id,
                    "check_in": entrada,
                    "check_out": saida,
                    "l10n_br_apuracao_dia_id": self.id,
                    "l10n_br_seq_par": indice,
                    "l10n_br_marcacao_entrada_id": por_momento.get(entrada).id
                    if por_momento.get(entrada)
                    else False,
                    "l10n_br_marcacao_saida_id": por_momento.get(saida).id
                    if por_momento.get(saida)
                    else False,
                }
            )
            for momento, tipo in ((entrada, "E"), (saida, "S")):
                marcacao = por_momento.get(momento)
                if marcacao:
                    marcacao.write(
                        {
                            "tipo_marcacao": tipo,
                            "seq_par": indice,
                            "state": "tratada",
                            "attendance_id": sessao.id,
                        }
                    )

    # ------------------------------------------------------------------
    # Construção a partir das marcações
    # ------------------------------------------------------------------

    @api.model
    def _gerar_dias(self, date_from, date_to, employees=None, company=None):
        """Cria (ou completa) as apurações do período a partir das marcações.

        Dias sem marcação também entram: é assim que a falta aparece. Ficam de
        fora os contratos dispensados de controle de jornada (art. 62).
        """
        company = company or self.env.company
        dominio_contrato = [
            ("state", "in", ("open", "close")),
            ("company_id", "=", company.id),
            ("date_start", "<=", date_to),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", date_from),
        ]
        if employees:
            dominio_contrato.append(("employee_id", "in", employees.ids))
        contratos = (
            self.env["hr.contract"]
            .search(dominio_contrato)
            ._l10n_br_sujeito_controle_jornada()
        )

        criados = self.browse()
        for contrato in contratos:
            criados |= self._gerar_dias_do_contrato(contrato, date_from, date_to)
        return criados

    @api.model
    def _gerar_dias_do_contrato(self, contrato, date_from, date_to):
        inicio = max(date_from, contrato.date_start)
        fim = min(date_to, contrato.date_end or date_to)
        existentes = {
            registro.date: registro
            for registro in self.search(
                [
                    ("employee_id", "=", contrato.employee_id.id),
                    ("date", ">=", inicio),
                    ("date", "<=", fim),
                ]
            )
        }
        marcacoes = self.env["l10n_br.hr.marcacao"].search(
            [
                ("employee_id", "=", contrato.employee_id.id),
                ("date_marcacao", ">=", inicio),
                ("date_marcacao", "<=", fim),
            ]
        )
        por_dia = {}
        for marcacao in marcacoes:
            por_dia.setdefault(marcacao.date_marcacao, self.env["l10n_br.hr.marcacao"])
            por_dia[marcacao.date_marcacao] |= marcacao

        dias = self.browse()
        data = inicio
        while data <= fim:
            registro = existentes.get(data)
            if not registro:
                registro = self.create(
                    {
                        "employee_id": contrato.employee_id.id,
                        "contract_id": contrato.id,
                        "company_id": contrato.company_id.id,
                        "date": data,
                    }
                )
            do_dia = por_dia.get(data)
            if do_dia:
                do_dia.write({"apuracao_dia_id": registro.id})
            dias |= registro
            data += timedelta(days=1)
        return dias
