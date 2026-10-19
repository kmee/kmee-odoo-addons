# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_br_sst_ambiente_id = fields.Many2one(
        "l10n_br.sst.ambiente",
        string="Ambiente de Trabalho",
        tracking=True,
        help="Ambiente onde o trabalhador exerce a atividade. É o que liga o "
        "contrato ao inventário de riscos e, por consequência, ao S-2240.",
    )
    l10n_br_sst_descricao_atividade = fields.Text(
        string="Descrição das Atividades (SST)",
        help="Descrição das atividades desempenhadas pelo trabalhador "
        "(dscAtivDes do S-2240). Vazio usa a descrição do ambiente.",
    )
    l10n_br_sst_risco_ids = fields.Many2many(
        "l10n_br.sst.risco",
        string="Riscos Aplicáveis",
        compute="_compute_l10n_br_sst_risco_ids",
        help="Riscos vigentes hoje no ambiente do contrato que atingem a "
        "função do trabalhador.",
    )
    l10n_br_sst_exposicao_especial = fields.Boolean(
        string="Exposição Ensejadora de Aposentadoria Especial",
        compute="_compute_l10n_br_sst_risco_ids",
    )

    @api.depends(
        "l10n_br_sst_ambiente_id",
        "l10n_br_sst_ambiente_id.risco_ids",
        "job_id",
    )
    def _compute_l10n_br_sst_risco_ids(self):
        hoje = fields.Date.context_today(self)
        for rec in self:
            riscos = rec._l10n_br_sst_riscos_vigentes(hoje)
            rec.l10n_br_sst_risco_ids = riscos
            rec.l10n_br_sst_exposicao_especial = bool(
                riscos._aliquota_gilrat_adicional()
            )

    def _l10n_br_sst_riscos_vigentes(self, data=None):
        """Riscos do ambiente vigentes na data que atingem a função do contrato.

        Args:
            data: data de referência; ``None`` usa a data de hoje.

        Returns:
            Recordset de ``l10n_br.sst.risco``.
        """
        self.ensure_one()
        if not self.l10n_br_sst_ambiente_id:
            return self.env["l10n_br.sst.risco"]
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        riscos = self.l10n_br_sst_ambiente_id.risco_ids
        return riscos._vigente_em(data)._aplica_a_funcao(self.job_id)

    def _l10n_br_sst_descricao_atividade(self):
        """Descrição das atividades para o S-2240, com queda para o ambiente."""
        self.ensure_one()
        return (
            self.l10n_br_sst_descricao_atividade
            or self.l10n_br_sst_ambiente_id.descricao_atividade
            or self.job_id.name
            or ""
        )
