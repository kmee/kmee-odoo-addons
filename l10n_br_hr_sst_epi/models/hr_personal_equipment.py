# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MOTIVO_DEVOLUCAO = [
    ("troca", "Troca por desgaste"),
    ("danificado", "Danificado"),
    ("vencido", "Prazo de validade vencido"),
    ("mudanca_funcao", "Mudança de função"),
    ("desligamento", "Desligamento"),
    ("outro", "Outro"),
]


class HrPersonalEquipment(models.Model):
    """Entrega de EPI com o que a NR-6 exige e a pilha da OCA não modela.

    O ciclo de vida (requisição, aceite, validação, expiração por cron) e a
    baixa de estoque continuam sendo os do ``hr_personal_equipment_request`` e
    do ``hr_employee_ppe``. Aqui entram o Certificado de Aprovação como
    entidade, o bloqueio de entrega com CA vencido, o registro de assinatura do
    trabalhador e o motivo de troca ou devolução.
    """

    _inherit = "hr.personal.equipment"

    l10n_br_sst_ca_id = fields.Many2one(
        "l10n_br.sst.ca",
        string="Certificado de Aprovação",
        tracking=True,
    )
    l10n_br_sst_ca_validade = fields.Date(
        related="l10n_br_sst_ca_id.validade",
        string="Validade do CA",
        readonly=True,
    )
    l10n_br_sst_ca_state = fields.Selection(
        related="l10n_br_sst_ca_id.state",
        string="Situação do CA",
        readonly=True,
    )
    l10n_br_sst_risco_ids = fields.Many2many(
        "l10n_br.sst.risco",
        string="Riscos Neutralizados",
        related="l10n_br_sst_ca_id.risco_neutralizado_ids",
        readonly=True,
    )
    certification = fields.Char(
        compute="_compute_certification",
        store=True,
        readonly=False,
    )
    l10n_br_sst_assinatura = fields.Binary(
        string="Assinatura do Trabalhador",
        attachment=True,
        help="Assinatura eletrônica do recebimento. A Portaria SIT 107/2009 "
        "admite o registro da entrega em sistema eletrônico.",
    )
    l10n_br_sst_data_assinatura = fields.Datetime(
        string="Data da Assinatura",
        readonly=True,
    )
    l10n_br_sst_motivo_devolucao = fields.Selection(
        MOTIVO_DEVOLUCAO,
        string="Motivo da Devolução",
        tracking=True,
    )
    l10n_br_sst_data_devolucao = fields.Date(
        string="Data da Devolução",
        tracking=True,
    )
    l10n_br_sst_observacao_devolucao = fields.Char(
        string="Observação da Devolução",
    )

    @api.depends("l10n_br_sst_ca_id")
    def _compute_certification(self):
        """O número de certificação passa a ser o do CA, quando há um."""
        for rec in self:
            if rec.l10n_br_sst_ca_id:
                rec.certification = rec.l10n_br_sst_ca_id.numero
            else:
                rec.certification = rec.certification

    @api.onchange("product_id")
    def _onchange_product_ca(self):
        if self.product_id.l10n_br_sst_ca_id:
            self.l10n_br_sst_ca_id = self.product_id.l10n_br_sst_ca_id

    def _l10n_br_sst_data_entrega(self):
        self.ensure_one()
        return self.start_date or fields.Date.context_today(self)

    def _check_ca_vigente(self):
        """Recusa a entrega de EPI cujo CA está vencido na data da entrega.

        A NR-6 só admite o uso de equipamento com Certificado de Aprovação
        válido, e a OCA expira a alocação, não o certificado. Sem esta trava,
        a ficha registra entrega que a fiscalização considera inexistente.
        """
        for rec in self:
            ca = rec.l10n_br_sst_ca_id
            if not ca:
                continue
            data = rec._l10n_br_sst_data_entrega()
            if not ca._vigente_em(data):
                raise UserError(
                    _(
                        "EPI %(produto)s: o Certificado de Aprovação %(ca)s "
                        "venceu em %(validade)s e não pode ser entregue em "
                        "%(data)s. Substitua o CA ou o equipamento."
                    )
                    % {
                        "produto": rec.product_id.display_name,
                        "ca": ca.numero,
                        "validade": ca.validade,
                        "data": data,
                    }
                )

    def _l10n_br_sst_produto_exige_ca(self):
        self.ensure_one()
        return self.product_id.is_ppe or self.is_ppe

    def _check_ca_informado(self):
        """EPI entregue sem CA não serve de prova em fiscalização."""
        for rec in self:
            if rec._l10n_br_sst_produto_exige_ca() and not rec.l10n_br_sst_ca_id:
                raise UserError(
                    _(
                        "EPI %(produto)s: informe o Certificado de Aprovação "
                        "antes de validar a entrega."
                    )
                    % {"produto": rec.product_id.display_name}
                )

    def validate_allocation(self):
        self._check_ca_informado()
        self._check_ca_vigente()
        return super().validate_allocation()

    def action_assinar(self):
        """Carimba a data da assinatura já anexada pelo trabalhador."""
        for rec in self:
            if not rec.l10n_br_sst_assinatura:
                raise UserError(
                    _("Anexe a assinatura do trabalhador antes de confirmar.")
                )
            rec.l10n_br_sst_data_assinatura = fields.Datetime.now()
        return True

    def action_devolver(self):
        """Registra a devolução ou troca do EPI, exigida pela NR-6."""
        for rec in self:
            if not rec.l10n_br_sst_motivo_devolucao:
                raise UserError(
                    _("Informe o motivo da devolução do EPI %(produto)s.")
                    % {"produto": rec.product_id.display_name}
                )
            rec.l10n_br_sst_data_devolucao = (
                rec.l10n_br_sst_data_devolucao or fields.Date.context_today(rec)
            )
            rec.expire_allocation()
        return True

    def _l10n_br_sst_valida_em(self, data):
        """Entregas ainda válidas na data, para efeito de S-2240 e de ficha."""
        data = fields.Date.to_date(data)
        return self.filtered(
            lambda r: r.state == "valid"
            and (not r.start_date or r.start_date <= data)
            and (not r.expiry_date or r.expiry_date >= data)
            and (
                not r.l10n_br_sst_data_devolucao or r.l10n_br_sst_data_devolucao > data
            )
        )
