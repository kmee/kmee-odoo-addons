# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

SIM_NAO = [("S", "Sim"), ("N", "Não")]

# Estados que impedem o fechamento: o evento periódico ainda não foi aceito.
ESTADOS_PENDENTES = ("draft", "validated", "pending", "sent", "error")


class ESocialS1299(models.Model):
    _name = "l10n_br.esocial.s1299"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1299 - Fechamento dos Eventos Periódicos"
    _order = "per_apur desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        required=True,
        help="AAAA-MM para a folha mensal, AAAA para o 13º salário.",
    )
    ind_apuracao = fields.Selection(
        [
            ("1", "Mensal"),
            ("2", "Anual (13º Salário)"),
        ],
        string="Tipo Apuração",
        default="1",
        required=True,
    )
    evt_remun = fields.Selection(
        SIM_NAO,
        string="Possui Eventos de Remuneração",
        compute="_compute_info_fech",
        store=True,
        readonly=False,
        help="Preenchido a partir dos S-1200 aceitos da competência.",
    )
    evt_pgtos = fields.Selection(
        SIM_NAO,
        string="Possui Eventos de Pagamento",
        compute="_compute_info_fech",
        store=True,
        readonly=False,
        help="Preenchido a partir dos S-1210 aceitos da competência.",
    )
    evt_com_prod = fields.Selection(
        SIM_NAO,
        string="Possui Comercialização de Produção",
        default="N",
        required=True,
    )
    evt_contrat_av_np = fields.Selection(
        SIM_NAO,
        string="Contratou Avulsos Não Portuários",
        default="N",
        required=True,
    )
    evt_info_compl_per = fields.Selection(
        SIM_NAO,
        string="Possui Informação Complementar",
        default="N",
        required=True,
    )
    trans_dctf_web = fields.Boolean(
        string="Transmitir DCTFWeb Imediatamente",
        help="Solicita a transmissão imediata da DCTFWeb no fechamento.",
    )
    nao_valid = fields.Boolean(
        string="Não Validar Fechamento",
        help="Solicita ao governo o fechamento sem as validações de "
        "consistência. Use apenas por orientação do fisco.",
    )
    pendencia_ids = fields.Many2many(
        "l10n_br.esocial.evento",
        string="Pendências",
        compute="_compute_pendencias",
        help="Eventos periódicos da competência que ainda não foram aceitos.",
    )
    pendencia_count = fields.Integer(compute="_compute_pendencias")

    @api.depends("per_apur", "ind_apuracao")
    def _compute_name(self):
        for rec in self:
            rec.name = f"S-1299 {rec.per_apur or ''}".strip()

    def _dominio_eventos_periodicos(self, tipos=None):
        """Domínio dos eventos periódicos da competência deste fechamento."""
        self.ensure_one()
        dominio = [
            ("company_id", "=", self.company_id.id),
            ("per_apur", "=", self.per_apur),
            ("tipo", "in", tipos or ["S-1200", "S-1210"]),
        ]
        return dominio

    @api.depends("per_apur", "company_id")
    def _compute_info_fech(self):
        eventos = self.env["l10n_br.esocial.evento"]
        for rec in self:
            if not rec.per_apur or not rec.company_id:
                rec.evt_remun = "N"
                rec.evt_pgtos = "N"
                continue
            aceitos = eventos.search(
                rec._dominio_eventos_periodicos() + [("state", "=", "success")]
            )
            tipos = set(aceitos.mapped("tipo"))
            rec.evt_remun = "S" if "S-1200" in tipos else "N"
            rec.evt_pgtos = "S" if "S-1210" in tipos else "N"

    @api.depends("per_apur", "company_id")
    def _compute_pendencias(self):
        eventos = self.env["l10n_br.esocial.evento"]
        for rec in self:
            if not rec.per_apur or not rec.company_id:
                rec.pendencia_ids = eventos
                rec.pendencia_count = 0
                continue
            pendentes = eventos.search(
                rec._dominio_eventos_periodicos()
                + [("state", "in", list(ESTADOS_PENDENTES))]
            )
            rec.pendencia_ids = pendentes
            rec.pendencia_count = len(pendentes)

    @api.constrains("per_apur", "ind_apuracao")
    def _check_per_apur(self):
        for rec in self:
            rec._validar_competencia(
                rec.per_apur, _("Período Apuração"), anual=rec.ind_apuracao == "2"
            )

    def _get_event_type(self):
        return "S-1299"

    def _prepare_evento_vals(self, xml, id_evento):
        vals = super()._prepare_evento_vals(xml, id_evento)
        vals["per_apur"] = self.per_apur
        return vals

    def _check_fechamento_pendente(self):
        """Recusa fechar competência que já tem um S-1299 aceito em aberto.

        Só é legítimo fechar de novo depois de uma reabertura (S-1298) aceita
        posterior ao fechamento anterior.
        """
        self.ensure_one()
        eventos = self.env["l10n_br.esocial.evento"]
        fechamentos = eventos.search(
            [
                ("company_id", "=", self.company_id.id),
                ("per_apur", "=", self.per_apur),
                ("tipo", "=", "S-1299"),
                ("state", "=", "success"),
            ],
            order="id desc",
            limit=1,
        )
        if not fechamentos:
            return
        # A ordem é dada pelo id, não por create_date: eventos criados na mesma
        # transação compartilham o timestamp e a comparação por data falharia.
        reaberturas = eventos.search_count(
            [
                ("company_id", "=", self.company_id.id),
                ("per_apur", "=", self.per_apur),
                ("tipo", "=", "S-1298"),
                ("state", "=", "success"),
                ("id", ">", fechamentos.id),
            ]
        )
        if not reaberturas:
            raise UserError(
                _(
                    "A competência %(per)s já está fechada (S-1299 aceito, "
                    "recibo %(recibo)s). Para enviar um novo fechamento, "
                    "transmita antes uma reabertura (S-1298)."
                )
                % {
                    "per": self.per_apur,
                    "recibo": fechamentos.nr_recibo or _("sem recibo"),
                }
            )

    def _check_pendencias(self):
        """Recusa fechar competência com evento periódico não aceito.

        Fechar com pendência faz o governo apurar sobre uma folha incompleta e
        o valor errado vai para a DCTFWeb — por isso a checagem é bloqueante.
        """
        self.ensure_one()
        pendentes = self.pendencia_ids
        if pendentes:
            detalhe = "\n".join(
                "- %s %s [%s]"
                % (
                    evento.tipo,
                    evento.id_evento or _("sem Id"),
                    dict(evento._fields["state"].selection).get(
                        evento.state, evento.state
                    ),
                )
                for evento in pendentes[:20]
            )
            raise UserError(
                _(
                    "Não é possível fechar a competência %(per)s: "
                    "%(qtd)s evento(s) periódico(s) ainda não foram aceitos "
                    "pelo eSocial.\n\n%(detalhe)s\n\n"
                    "Transmita e confirme o aceite desses eventos (ou exclua-os "
                    "com S-3000) antes do fechamento."
                )
                % {
                    "per": self.per_apur,
                    "qtd": len(pendentes),
                    "detalhe": detalhe,
                }
            )
        if self.evt_remun == "S" and not self.env[
            "l10n_br.esocial.evento"
        ].search_count(
            self._dominio_eventos_periodicos(["S-1200"]) + [("state", "=", "success")]
        ):
            raise UserError(
                _(
                    "O fechamento declara eventos de remuneração ('Sim') mas "
                    "não existe nenhum S-1200 aceito na competência %(per)s."
                )
                % {"per": self.per_apur}
            )

    def action_gerar_evento(self):
        """Valida as pendências da competência antes de gerar o fechamento."""
        self.ensure_one()
        self._check_fechamento_pendente()
        self._check_pendencias()
        return super().action_gerar_evento()

    def _to_esociallib_dict(self):
        self.ensure_one()
        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "ind_apuracao": int(self.ind_apuracao),
            "per_apur": self.per_apur,
            "evt_remun": self.evt_remun or "N",
            "evt_pgtos": self.evt_pgtos or "N",
            "evt_com_prod": self.evt_com_prod,
            "evt_contrat_av_np": self.evt_contrat_av_np,
            "evt_info_compl_per": self.evt_info_compl_per,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }
        if self.trans_dctf_web:
            data["trans_dctf_web"] = "S"
        if self.nao_valid:
            data["nao_valid"] = "S"
        return data
