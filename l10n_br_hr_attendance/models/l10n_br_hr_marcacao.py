# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Fonte da marcação no registro tipo "05" do AEJ (Anexo VI, campo fonteMarc).
FONTE_MARCACAO_AEJ = {
    "rep_c": "O",
    "rep_a": "O",
    "rep_p": "O",
    "manual": "I",
    "pre_assinalada": "P",
    "excecao": "X",
    "outra": "T",
}

ORIGEM_MARCACAO = [
    ("rep_c", "REP-C"),
    ("rep_a", "REP-A"),
    ("rep_p", "REP-P"),
    ("manual", "Incluída manualmente"),
    ("pre_assinalada", "Pré-assinalada"),
    ("excecao", "Ponto por exceção"),
    ("outra", "Outra fonte"),
]

# Identificador do coletor da marcação (Anexo V, registro tipo "7", campo 6).
COLETOR_MARCACAO = [
    ("01", "Aplicativo mobile"),
    ("02", "Browser (navegador internet)"),
    ("03", "Aplicativo desktop"),
    ("04", "Dispositivo eletrônico"),
    ("05", "Outro dispositivo eletrônico"),
]


class L10nBrHrMarcacao(models.Model):
    """Marcação de ponto individual, imutável, tal como registrada pelo REP.

    Este é o dado de origem do art. 82 da Portaria 671/2021: o PTRP pode
    apenas complementar omissões e indicar marcações indevidas, nunca alterar
    o registro original. Por isso a marcação original é gravada aqui e nunca
    sofre ``write``; o tratamento nasce como um NOVO registro que aponta para
    o original em ``marcacao_origem_id``.

    O ``hr.attendance`` do Odoo continua existindo, mas como visão derivada
    (par entrada/saída), montada pelo módulo de apuração a partir daqui.
    """

    _name = "l10n_br.hr.marcacao"
    _description = "Marcação de Ponto"
    _order = "datetime_marcacao desc, nsr desc"
    _rec_name = "display_name"

    # Campos que descrevem o FATO registrado pelo REP. Alterá-los seria
    # adulteração (art. 74, IV e art. 98) - o ORM recusa o write.
    _CAMPOS_IMUTAVEIS = (
        "nsr",
        "rep_id",
        "datetime_marcacao",
        "cpf",
        "pis_pasep",
        "origem",
        "hash_registro",
        "hash_anterior",
        "coletor",
        "offline",
    )

    nsr = fields.Integer(
        string="NSR",
        required=True,
        readonly=True,
        index=True,
        help="Número Sequencial de Registro atribuído pelo REP.",
    )
    rep_id = fields.Many2one(
        comodel_name="l10n_br.hr.rep",
        string="REP",
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Funcionário",
        index=True,
        help="Preenchido pela conciliação por CPF/PIS. Marcação sem "
        "funcionário fica pendente e nunca é descartada.",
    )
    cpf = fields.Char(
        string="CPF (arquivo)",
        readonly=True,
        help="CPF exatamente como veio do REP, usado na conciliação.",
    )
    pis_pasep = fields.Char(
        string="PIS/PASEP (arquivo)",
        readonly=True,
        help="Chave de conciliação dos REPs no leiaute da Portaria 1.510/2009.",
    )
    datetime_marcacao = fields.Datetime(
        string="Data/hora da marcação",
        required=True,
        readonly=True,
        index=True,
    )
    datetime_gravacao = fields.Datetime(
        string="Data/hora da gravação",
        readonly=True,
        help="Momento em que o REP-P gravou o registro (Anexo V, tipo 7).",
    )
    date_marcacao = fields.Date(
        string="Dia",
        compute="_compute_date_marcacao",
        store=True,
        index=True,
        help="Dia da marcação no fuso do funcionário, base da apuração diária.",
    )
    origem = fields.Selection(
        selection=ORIGEM_MARCACAO,
        required=True,
        readonly=True,
        default="rep_c",
    )
    fonte_aej = fields.Selection(
        selection=[
            ("O", "O - original do REP"),
            ("I", "I - incluída manualmente"),
            ("P", "P - pré-assinalada"),
            ("X", "X - ponto por exceção"),
            ("T", "T - outras fontes"),
        ],
        string="Fonte (AEJ)",
        compute="_compute_fonte_aej",
        store=True,
    )
    tipo_marcacao = fields.Selection(
        selection=[
            ("E", "Entrada"),
            ("S", "Saída"),
            ("D", "Desconsiderada"),
        ],
        string="Tipo",
        help="Atribuído pelo tratamento (pareamento). Marcação desconsiderada "
        "permanece no arquivo com o motivo, nunca é apagada.",
    )
    seq_par = fields.Integer(
        string="Par entrada/saída",
        default=0,
        help="Número sequencial do par entrada/saída no dia (registro 05 do AEJ).",
    )
    state = fields.Selection(
        selection=[
            ("original", "Original"),
            ("tratada", "Tratada"),
            ("desconsiderada", "Desconsiderada"),
        ],
        default="original",
        required=True,
        index=True,
    )
    marcacao_origem_id = fields.Many2one(
        comodel_name="l10n_br.hr.marcacao",
        string="Marcação de origem",
        readonly=True,
        ondelete="restrict",
        help="Registro original que este tratamento corrige ou complementa "
        "(art. 82). O original permanece intacto.",
    )
    tratamento_ids = fields.One2many(
        comodel_name="l10n_br.hr.marcacao",
        inverse_name="marcacao_origem_id",
        string="Tratamentos",
    )
    motivo = fields.Char(
        help="Motivo da desconsideração ou da inclusão manual. Obrigatório "
        "quando o tipo é 'Desconsiderada' ou a fonte é 'incluída manualmente' "
        "(Anexo VI, registro 05, campo motivo).",
    )
    user_tratamento_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsável pelo tratamento",
        readonly=True,
    )
    hash_registro = fields.Char(
        string="Hash SHA-256",
        readonly=True,
        help="Código hash do registro tipo 7 do AFD (REP-P).",
    )
    hash_anterior = fields.Char(
        string="Hash anterior",
        readonly=True,
        help="Hash do registro imediatamente anterior, que encadeia a série.",
    )
    coletor = fields.Selection(
        selection=COLETOR_MARCACAO,
        readonly=True,
    )
    offline = fields.Boolean(
        readonly=True,
        help="Marcação coletada off-line (campo 7 do registro tipo 7).",
    )
    attendance_id = fields.Many2one(
        comodel_name="hr.attendance",
        string="Sessão (hr.attendance)",
        ondelete="set null",
        help="Par entrada/saída derivado desta marcação.",
    )

    _sql_constraints = [
        (
            "nsr_rep_uniq",
            "unique(rep_id, nsr)",
            "O NSR deve ser único por REP: já existe marcação com este número.",
        ),
    ]

    @api.depends("datetime_marcacao", "employee_id")
    def _compute_date_marcacao(self):
        for rec in self:
            if not rec.datetime_marcacao:
                rec.date_marcacao = False
                continue
            tz = rec.employee_id.tz or self.env.user.tz or "America/Sao_Paulo"
            rec.date_marcacao = fields.Datetime.context_timestamp(
                rec.with_context(tz=tz), rec.datetime_marcacao
            ).date()

    @api.depends("origem")
    def _compute_fonte_aej(self):
        for rec in self:
            rec.fonte_aej = FONTE_MARCACAO_AEJ.get(rec.origem, "T")

    def name_get(self):
        resultado = []
        for rec in self:
            nome = rec.employee_id.name or rec.cpf or rec.pis_pasep or _("pendente")
            data = (
                fields.Datetime.to_string(rec.datetime_marcacao)
                if rec.datetime_marcacao
                else ""
            )
            resultado.append((rec.id, "%s - %s (NSR %s)" % (nome, data, rec.nsr)))
        return resultado

    @api.constrains("tipo_marcacao", "origem", "motivo")
    def _check_motivo(self):
        """Anexo VI: motivo é obrigatório para desconsideração e inclusão."""
        for rec in self:
            exige_motivo = rec.tipo_marcacao == "D" or rec.origem == "manual"
            if exige_motivo and not rec.motivo:
                raise ValidationError(
                    _(
                        "Informe o motivo: marcações desconsideradas ou "
                        "incluídas manualmente exigem justificativa "
                        "(Portaria 671/2021, art. 82)."
                    )
                )

    @api.constrains("nsr")
    def _check_nsr_positivo(self):
        for rec in self:
            if rec.nsr < 1:
                raise ValidationError(
                    _("O NSR deve iniciar em 1 e ser sempre positivo (Anexo V).")
                )

    def write(self, vals):
        """Bloqueia alteração dos campos que descrevem o fato registrado.

        Nada impede completar a conciliação (``employee_id`` vazio), classificar
        o par entrada/saída ou desconsiderar a marcação com motivo - esses são
        atos de TRATAMENTO, permitidos pelo art. 82. O que não se altera é o
        registro em si.
        """
        protegidos = [campo for campo in self._CAMPOS_IMUTAVEIS if campo in vals]
        if protegidos and not self.env.context.get("l10n_br_gravando_marcacao"):
            raise UserError(
                _(
                    "Marcação de ponto é registro imutável (Portaria 671/2021, "
                    "art. 74, IV e art. 82). Campos recusados: %s.\n"
                    "Para corrigir, registre um tratamento vinculado ao "
                    "original."
                )
                % ", ".join(protegidos)
            )
        if "employee_id" in vals:
            ja_conciliadas = self.filtered(
                lambda m: m.employee_id and m.employee_id.id != vals["employee_id"]
            )
            if ja_conciliadas and not self.env.context.get("l10n_br_gravando_marcacao"):
                raise UserError(
                    _(
                        "A marcação já está vinculada a um funcionário. Trocar "
                        "o vínculo alteraria o registro original; desconsidere "
                        "a marcação com motivo e inclua o tratamento correto."
                    )
                )
        return super().write(vals)

    def unlink(self):
        """Marcação nunca é apagada: o AFD é imutável e auditável."""
        if not self.env.context.get("l10n_br_gravando_marcacao"):
            raise UserError(
                _(
                    "Marcação de ponto não pode ser excluída (Portaria "
                    "671/2021, art. 74, IV). Use a desconsideração com motivo, "
                    "que preserva o registro e explica a correção."
                )
            )
        return super().unlink()

    def action_desconsiderar(self, motivo=None):
        """Marca a ocorrência como desconsiderada, preservando o registro."""
        motivo = motivo or self.env.context.get("l10n_br_motivo")
        if not motivo:
            raise UserError(
                _("Informe o motivo da desconsideração (Anexo VI, registro 05).")
            )
        return self.write(
            {
                "tipo_marcacao": "D",
                "state": "desconsiderada",
                "motivo": motivo,
                "user_tratamento_id": self.env.user.id,
            }
        )

    @api.model
    def _calcular_hash(
        self,
        nsr,
        tipo,
        dh_marcacao,
        cpf,
        dh_gravacao,
        coletor,
        offline,
        hash_anterior="",
    ):
        """SHA-256 do registro tipo 7 do AFD (Anexo V, item 9).

        A base é a concatenação dos campos 1 a 7 do registro mais o hash do
        registro anterior, quando existir - é isso que encadeia a série e faz
        qualquer reescrita retroativa saltar aos olhos.
        """
        base = "%s%s%s%s%s%s%s%s" % (
            str(nsr).zfill(9),
            tipo,
            dh_marcacao,
            str(cpf or "").zfill(12),
            dh_gravacao,
            coletor,
            "1" if offline else "0",
            hash_anterior or "",
        )
        return hashlib.sha256(base.encode("iso-8859-1", errors="replace")).hexdigest()

    @api.model
    def _criar_marcacoes(self, vals_list):
        """Cria marcações com os campos imutáveis liberados uma única vez.

        A permissão morre no create: o recordset devolvido volta com a trava
        ligada, senão qualquer código que reaproveitasse o retorno herdaria o
        contexto e escreveria por cima do registro original sem perceber.
        """
        criadas = self.with_context(l10n_br_gravando_marcacao=True).create(vals_list)
        return criadas.with_context(l10n_br_gravando_marcacao=False)

    def _conciliar_funcionario(self, employee):
        """Vincula a marcação pendente ao funcionário identificado.

        Só atua sobre marcações ainda sem vínculo: completar uma omissão é
        tratamento permitido; trocar um vínculo já estabelecido não é.
        """
        pendentes = self.filtered(lambda m: not m.employee_id)
        if pendentes:
            pendentes.write({"employee_id": employee.id})
        return pendentes
