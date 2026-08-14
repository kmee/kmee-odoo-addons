# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Códigos da Tabela 71 (tpCAT).
TIPO_CAT_INICIAL = "1"
TIPO_CAT_REABERTURA = "2"
TIPO_CAT_OBITO = "3"


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
        help="Tabela 71 do eSocial: inicial, reabertura ou comunicação de óbito.",
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
        help="Primeiro dia útil seguinte ao acidente. Em caso de óbito, a "
        "comunicação é imediata e o prazo é o próprio dia do acidente.",
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
            if acidente.houve_obito:
                # Óbito é comunicação imediata: não há dia útil seguinte.
                limite = acidente.date_acidente
            else:
                limite = rec._proximo_dia_util(acidente.date_acidente)
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
    def _proximo_dia_util(self, data):
        """Primeiro dia útil seguinte à data, pulando fim de semana e feriado.

        Os feriados vêm da Tabela 84 do eSocial, cujo código traz a data no
        formato DDMMAAAA. Feriado móvel de ano não coberto pela tabela não é
        adivinhado: nesse caso vale só o fim de semana, que é o mínimo seguro.
        """
        data = fields.Date.to_date(data)
        feriados = self._datas_feriado()
        candidato = data + timedelta(days=1)
        for _tentativa in range(15):
            if candidato.weekday() < 5 and candidato not in feriados:
                return candidato
            candidato += timedelta(days=1)
        return candidato

    @api.model
    def _datas_feriado(self):
        datas = set()
        for feriado in self.env["l10n_br.esocial.feriado"].search([]):
            codigo = (feriado.codigo or "").strip()
            if len(codigo) != 8 or not codigo.isdigit():
                continue
            try:
                datas.add(
                    fields.Date.to_date(
                        "%s-%s-%s" % (codigo[4:], codigo[2:4], codigo[:2])
                    )
                )
            except ValueError:
                continue
        return datas

    @api.constrains("tipo_cat_id", "cat_origem_id")
    def _check_cat_origem(self):
        """Reabertura e óbito referenciam a CAT anterior (regra do S-2210)."""
        for rec in self:
            if rec.tipo_cat_codigo in (TIPO_CAT_REABERTURA, TIPO_CAT_OBITO) and not (
                rec.cat_origem_id or rec.nr_rec_cat_orig
            ):
                raise UserError(
                    _(
                        "CAT de %(tipo)s exige a CAT de origem ou o recibo da "
                        "comunicação anterior."
                    )
                    % {"tipo": rec.tipo_cat_id.nome}
                )

    def action_emitir(self):
        """Emite a CAT e avisa quando o prazo legal já passou."""
        for rec in self:
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
        pendentes = self.search(
            [
                ("state", "=", "draft"),
                ("date_limite", "<=", fields.Date.context_today(self)),
            ]
        )
        for cat in pendentes:
            cat.message_post(
                body=_(
                    "CAT ainda em rascunho com prazo legal em %(limite)s. A "
                    "comunicação do acidente é obrigatória até o primeiro dia "
                    "útil seguinte."
                )
                % {"limite": cat.date_limite}
            )
        return pendentes
