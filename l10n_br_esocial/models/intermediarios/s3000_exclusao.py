# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Eventos periódicos cuja exclusão exige a identificação da folha (ideFolhaPagto).
TIPOS_COM_FOLHA = (
    "S-1200",
    "S-1202",
    "S-1207",
    "S-1210",
    "S-1260",
    "S-1270",
    "S-1280",
    "S-1298",
    "S-1299",
)
# Eventos cuja exclusão exige a identificação do trabalhador (ideTrabalhador).
TIPOS_COM_TRABALHADOR = (
    "S-1200",
    "S-1202",
    "S-1207",
    "S-1210",
    "S-2190",
    "S-2200",
    "S-2205",
    "S-2206",
    "S-2210",
    "S-2220",
    "S-2221",
    "S-2230",
    "S-2231",
    "S-2240",
    "S-2298",
    "S-2299",
    "S-2300",
    "S-2306",
    "S-2399",
    "S-2400",
)


class ESocialS3000(models.Model):
    _name = "l10n_br.esocial.s3000"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-3000 - Exclusão de Eventos"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    evento_origem_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Evento a Excluir",
        required=True,
        ondelete="cascade",
        domain="[('state', '=', 'success')]",
        help="Evento já aceito pelo eSocial que se pretende excluir.",
    )
    tp_evento = fields.Char(
        string="Tipo do Evento Excluído",
        related="evento_origem_id.tipo",
        store=True,
        readonly=True,
    )
    nr_rec_evt = fields.Char(
        string="Recibo do Evento Excluído",
        related="evento_origem_id.nr_recibo",
        store=True,
        readonly=True,
    )
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        help="Competência do evento excluído. Obrigatório para eventos " "periódicos.",
    )
    ind_apuracao = fields.Selection(
        [
            ("1", "Mensal"),
            ("2", "Anual (13º Salário)"),
        ],
        string="Tipo Apuração",
    )
    cpf_trab = fields.Char(
        string="CPF do Trabalhador",
        size=11,
        help="Obrigatório para eventos não periódicos e para os periódicos por "
        "trabalhador (S-1200 a S-1210).",
    )
    motivo = fields.Text(
        string="Motivo da Exclusão",
        help="Registro interno de auditoria — não é transmitido ao eSocial.",
    )

    @api.depends("tp_evento", "nr_rec_evt")
    def _compute_name(self):
        for rec in self:
            rec.name = " - ".join(
                parte for parte in ("S-3000", rec.tp_evento, rec.nr_rec_evt) if parte
            )

    @api.onchange("evento_origem_id")
    def _onchange_evento_origem_id(self):
        """Herda competência e trabalhador do evento a excluir."""
        for rec in self:
            origem = rec.evento_origem_id
            if not origem:
                continue
            rec.per_apur = origem.per_apur
            if origem.per_apur and not rec.ind_apuracao:
                rec.ind_apuracao = "1" if "-" in origem.per_apur else "2"
            rec.cpf_trab = rec._buscar_cpf_origem(origem)

    @api.model
    def _buscar_cpf_origem(self, evento):
        """CPF do trabalhador do intermediário que originou o evento."""
        if not evento.origem_model or not evento.origem_id:
            return False
        if evento.origem_model not in self.env:
            return False
        origem = self.env[evento.origem_model].browse(evento.origem_id).exists()
        if not origem or "employee_id" not in origem._fields:
            return False
        cpf = origem.employee_id.cnpj_cpf
        return self._so_digitos(cpf) if cpf else False

    def _get_event_type(self):
        return "S-3000"

    def _prepare_evento_vals(self, xml, id_evento):
        vals = super()._prepare_evento_vals(xml, id_evento)
        vals.update(
            {
                "operacao": "E",
                "per_apur": self.per_apur,
                "evento_excluido_id": self.evento_origem_id.id,
            }
        )
        return vals

    def _check_origem(self):
        self.ensure_one()
        origem = self.evento_origem_id
        if origem.company_id != self.company_id:
            raise UserError(
                _(
                    "O evento %(nome)s pertence a outra empresa "
                    "(%(empresa)s): a exclusão tem de sair do mesmo "
                    "empregador que transmitiu o evento."
                )
                % {"nome": origem.name, "empresa": origem.company_id.name}
            )
        if origem.state != "success":
            raise UserError(
                _(
                    "Só é possível excluir evento aceito pelo eSocial. O evento "
                    "%(nome)s está em '%(estado)s'."
                )
                % {"nome": origem.name, "estado": origem.state}
            )
        if not origem.nr_recibo:
            raise UserError(
                _(
                    "O evento %(nome)s não possui recibo de entrega. A exclusão "
                    "identifica o evento pelo recibo, então ele é obrigatório."
                )
                % {"nome": origem.name}
            )
        self._validar_nr_recibo(origem.nr_recibo, _("Recibo do Evento Excluído"))
        if origem.tipo in TIPOS_COM_FOLHA and not self.per_apur:
            raise UserError(
                _(
                    "A exclusão de %(tipo)s exige o período de apuração do "
                    "evento excluído."
                )
                % {"tipo": origem.tipo}
            )
        if origem.tipo in TIPOS_COM_TRABALHADOR and not self.cpf_trab:
            raise UserError(
                _(
                    "A exclusão de %(tipo)s exige o CPF do trabalhador do "
                    "evento excluído."
                )
                % {"tipo": origem.tipo}
            )
        ja_excluido = self.env["l10n_br.esocial.evento"].search_count(
            [
                ("tipo", "=", "S-3000"),
                ("evento_excluido_id", "=", origem.id),
                ("state", "in", ("draft", "validated", "pending", "sent", "success")),
            ]
        )
        if ja_excluido:
            raise UserError(
                _(
                    "Já existe um S-3000 em andamento ou aceito para o evento "
                    "%(nome)s."
                )
                % {"nome": origem.name}
            )

    def action_gerar_evento(self):
        self.ensure_one()
        self._check_origem()
        return super().action_gerar_evento()

    def _to_esociallib_dict(self):
        self.ensure_one()
        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "tp_evento": self.tp_evento,
            "nr_rec_evt": self.nr_rec_evt,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }
        if self.cpf_trab:
            data["cpf_trab"] = self._so_digitos(self.cpf_trab)
        if self.per_apur:
            data["per_apur"] = self.per_apur
            data["ind_apuracao"] = int(self.ind_apuracao or "1")
        return data
