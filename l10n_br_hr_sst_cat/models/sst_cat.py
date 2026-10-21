# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Domínio fixo de tpCat do S-2210 (não é tabela do Anexo I do eSocial).
TIPO_CAT_INICIAL = "1"
TIPO_CAT_REABERTURA = "2"
TIPO_CAT_OBITO = "3"

# Feriados civis nacionais de data fixa: Lei 662/1949 (com a redação da Lei
# 10.607/2002), Lei 6.802/1980 (12 de outubro) e Lei 14.759/2023 (20 de
# novembro, a partir de 2024). Não há feriado nacional móvel: Carnaval, Sexta-
# feira da Paixão e Corpus Christi não são feriados nacionais (os religiosos
# são municipais, Lei 9.093/1995, art. 1, III), e só contam se configurados no
# calendário da empresa.
FERIADOS_NACIONAIS = (
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (12, 25),
)
CONSCIENCIA_NEGRA = (11, 20)
CONSCIENCIA_NEGRA_DESDE = 2024


class L10nBrSstCat(models.Model):
    """Comunicação de Acidente de Trabalho.

    O art. 22 da Lei 8.213/91 manda comunicar o acidente até o primeiro dia
    útil seguinte e, em caso de óbito, de imediato. Desde 2023 a comunicação é
    o próprio S-2210, e o descumprimento do prazo gera multa, por isso o prazo
    é calculado e acompanhado aqui, e não deixado à memória de quem opera.
    """

    _name = "l10n_br.sst.cat"
    _description = "SST - Comunicação de Acidente de Trabalho"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_emissao desc, id desc"

    name = fields.Char(
        string="Identificação",
        compute="_compute_name",
        store=True,
    )
    acidente_id = fields.Many2one(
        "l10n_br.sst.acidente",
        string="Acidente",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="acidente_id.company_id",
        store=True,
        readonly=True,
    )
    employee_id = fields.Many2one(
        related="acidente_id.employee_id",
        store=True,
        readonly=True,
    )
    tipo_cat_id = fields.Many2one(
        "l10n_br.esocial.tipo.cat",
        string="Tipo de CAT",
        required=True,
        tracking=True,
        help="Campo tpCat do S-2210 (domínio do leiaute): inicial, reabertura "
        "ou comunicação de óbito.",
    )
    tipo_cat_codigo = fields.Char(
        related="tipo_cat_id.codigo",
        store=True,
    )
    date_emissao = fields.Date(
        string="Data de Emissão",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    numero_recibo = fields.Char(
        string="Recibo do eSocial",
        readonly=True,
        copy=False,
    )
    cat_origem_id = fields.Many2one(
        "l10n_br.sst.cat",
        string="CAT de Origem",
        help="CAT anterior, obrigatória na reabertura e na comunicação de óbito.",
    )
    nr_rec_cat_orig = fields.Char(
        string="Recibo da CAT de Origem",
        compute="_compute_nr_rec_cat_orig",
        store=True,
        readonly=False,
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("emitida", "Emitida"),
            ("transmitida", "Transmitida"),
            ("cancelled", "Cancelada"),
        ],
        string="Situação",
        default="draft",
        required=True,
        tracking=True,
    )
    date_limite = fields.Date(
        string="Prazo Legal",
        compute="_compute_prazo",
        store=True,
        help="Primeiro dia útil seguinte ao acidente (Lei 8.213/91, art. 22). "
        "Em caso de óbito, a comunicação é imediata, contada da data do óbito. "
        "Dia útil exclui sábado, domingo, feriado nacional e os feriados "
        "configurados no calendário da empresa.",
    )
    alerta_prazo_date = fields.Date(
        string="Último Alerta de Prazo",
        readonly=True,
        copy=False,
        help="Data do último alerta do cron, para não repetir o aviso no " "mesmo dia.",
    )
    prazo_situacao = fields.Selection(
        [
            ("no_prazo", "No prazo"),
            ("hoje", "Vence hoje"),
            ("atrasada", "Fora do prazo"),
        ],
        string="Situação do Prazo",
        compute="_compute_prazo",
        store=True,
    )

    @api.depends("acidente_id", "tipo_cat_id")
    def _compute_name(self):
        for rec in self:
            partes = [rec.tipo_cat_id.nome, rec.acidente_id.name]
            rec.name = " - ".join(p for p in partes if p)

    @api.depends("cat_origem_id.numero_recibo")
    def _compute_nr_rec_cat_orig(self):
        for rec in self:
            rec.nr_rec_cat_orig = rec.cat_origem_id.numero_recibo or False

    @api.depends(
        "acidente_id.date_acidente",
        "acidente_id.houve_obito",
        "acidente_id.date_obito",
        "tipo_cat_id",
        "date_emissao",
        "state",
    )
    def _compute_prazo(self):
        hoje = fields.Date.context_today(self)
        for rec in self:
            acidente = rec.acidente_id
            if not acidente.date_acidente:
                rec.date_limite = False
                rec.prazo_situacao = False
                continue
            if rec.tipo_cat_codigo == TIPO_CAT_REABERTURA:
                # A reabertura não nasce da data do acidente: contar o prazo
                # dele a deixaria sempre "fora do prazo". Sem prazo calculado.
                rec.date_limite = False
                rec.prazo_situacao = False
                continue
            if rec.tipo_cat_codigo == TIPO_CAT_OBITO and acidente.date_obito:
                # Comunicação de óbito é imediata, contada do óbito.
                limite = acidente.date_obito
            else:
                limite = rec._proximo_dia_util(acidente.date_acidente, rec.company_id)
                if acidente.houve_obito and acidente.date_obito:
                    # Morte antes do dia útil seguinte torna a comunicação
                    # imediata a partir do óbito; morte depois dele não
                    # antecipa o prazo da CAT inicial.
                    limite = min(limite, acidente.date_obito)
            rec.date_limite = limite
            referencia = (
                rec.date_emissao if rec.state in ("emitida", "transmitida") else hoje
            )
            if referencia > limite:
                rec.prazo_situacao = "atrasada"
            elif referencia == limite:
                rec.prazo_situacao = "hoje"
            else:
                rec.prazo_situacao = "no_prazo"

    @api.model
    def _proximo_dia_util(self, data, company=None):
        """Primeiro dia útil seguinte à data.

        Dia útil é qualquer dia exceto sábado, domingo, feriado nacional e os
        feriados configurados no calendário de trabalho da empresa (estaduais
        e municipais). Nenhuma norma define o calendário da CAT; contar menos
        feriados antecipa o prazo, que é o lado seguro.
        """
        data = fields.Date.to_date(data)
        company = company or self.env.company
        candidato = data + timedelta(days=1)
        anos = {candidato.year, candidato.year + 1}
        feriados = self._datas_feriado(anos, company)
        for _tentativa in range(15):
            if candidato.weekday() < 5 and candidato not in feriados:
                return candidato
            candidato += timedelta(days=1)
        return candidato

    @api.model
    def _datas_feriado(self, anos, company=None):
        """Feriados nacionais dos anos informados e os locais da empresa."""
        datas = set()
        for ano in anos:
            datas.update(date(ano, mes, dia) for mes, dia in FERIADOS_NACIONAIS)
            if ano >= CONSCIENCIA_NEGRA_DESDE:
                datas.add(date(ano, *CONSCIENCIA_NEGRA))
        calendario = (company or self.env.company).resource_calendar_id
        if calendario:
            datas.update(self._datas_feriado_do_calendario(calendario))
        return datas

    @api.model
    def _datas_feriado_do_calendario(self, calendario):
        """Dias cobertos pelas folgas gerais do calendário, no fuso dele."""
        fuso = pytz.timezone(calendario.tz or "UTC")
        datas = set()
        for folga in calendario.global_leave_ids:
            inicio = pytz.utc.localize(folga.date_from).astimezone(fuso).date()
            fim = pytz.utc.localize(folga.date_to).astimezone(fuso).date()
            while inicio <= fim:
                datas.add(inicio)
                inicio += timedelta(days=1)
        return datas

    @api.constrains("tipo_cat_id", "cat_origem_id")
    def _check_cat_origem(self):
        """Reabertura e óbito referenciam a CAT anterior (regra do S-2210)."""
        for rec in self:
            if rec.tipo_cat_codigo in (TIPO_CAT_REABERTURA, TIPO_CAT_OBITO) and not (
                rec.cat_origem_id or rec.nr_rec_cat_orig
            ):
                raise ValidationError(
                    _(
                        "CAT de %(tipo)s exige a CAT de origem ou o recibo da "
                        "comunicação anterior."
                    )
                    % {"tipo": rec.tipo_cat_id.nome}
                )

    def action_emitir(self):
        """Emite a CAT e avisa quando o prazo legal já passou."""
        for rec in self:
            if rec.state != "draft":
                continue
            rec.state = "emitida"
            rec._compute_prazo()
            if rec.prazo_situacao == "atrasada":
                rec.message_post(
                    body=_(
                        "CAT emitida fora do prazo do art. 22 da Lei 8.213/91: "
                        "o limite era %(limite)s e a emissão foi em %(emissao)s."
                    )
                    % {"limite": rec.date_limite, "emissao": rec.date_emissao}
                )
            if rec.acidente_id.state == "registrado":
                rec.acidente_id.state = "comunicado"
        return True

    def action_cancelar(self):
        self.write({"state": "cancelled"})

    @api.model
    def cron_alerta_prazo(self):
        """Cobra as CATs cujo prazo legal vence hoje ou já venceu."""
        hoje = fields.Date.context_today(self)
        rascunhos = self.search(
            [("state", "=", "draft"), ("acidente_id.state", "!=", "cancelled")]
        )
        # O prazo depende do dia de hoje, que não dispara o recálculo sozinho.
        rascunhos._compute_prazo()
        pendentes = rascunhos.filtered(
            lambda c: c.date_limite
            and c.date_limite <= hoje
            and c.alerta_prazo_date != hoje
        )
        for cat in pendentes:
            cat.alerta_prazo_date = hoje
            cat.message_post(
                body=_(
                    "CAT ainda em rascunho com prazo legal em %(limite)s. A "
                    "comunicação do acidente é obrigatória até o primeiro dia "
                    "útil seguinte."
                )
                % {"limite": cat.date_limite}
            )
        return pendentes
