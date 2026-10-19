# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .hr_employee_medical_examination import TIPO_ASO_RETORNO

# Afastamento a partir de 30 dias exige exame de retorno ao trabalho (NR-7).
DIAS_AFASTAMENTO_RETORNO = 30


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_sst_aso_vencimento = fields.Date(
        string="Vencimento do ASO",
        compute="_compute_l10n_br_sst_aso",
        store=True,
    )
    l10n_br_sst_aso_situacao = fields.Selection(
        [
            ("sem_aso", "Sem ASO"),
            ("em_dia", "Em dia"),
            ("a_vencer", "A vencer"),
            ("vencido", "Vencido"),
        ],
        string="Situação do ASO",
        compute="_compute_l10n_br_sst_aso",
        store=True,
    )

    @api.depends(
        "medical_examination_ids.l10n_br_date_vencimento",
        "medical_examination_ids.state",
    )
    def _compute_l10n_br_sst_aso(self):
        hoje = fields.Date.context_today(self)
        for rec in self:
            concluidos = rec.medical_examination_ids.filtered(
                lambda e: e.state == "done" and e.l10n_br_date_vencimento
            )
            if not concluidos:
                rec.l10n_br_sst_aso_vencimento = False
                rec.l10n_br_sst_aso_situacao = "sem_aso"
                continue
            vencimento = max(concluidos.mapped("l10n_br_date_vencimento"))
            rec.l10n_br_sst_aso_vencimento = vencimento
            dias = rec.company_id.l10n_br_sst_aso_alerta_dias or 30
            if vencimento < hoje:
                rec.l10n_br_sst_aso_situacao = "vencido"
            elif vencimento <= hoje + relativedelta(days=dias):
                rec.l10n_br_sst_aso_situacao = "a_vencer"
            else:
                rec.l10n_br_sst_aso_situacao = "em_dia"

    def _l10n_br_sst_idade(self, data=None):
        """Idade do trabalhador na data, usada pelas faixas do PCMSO."""
        self.ensure_one()
        if not self.birthday:
            return None
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        return relativedelta(data, self.birthday).years

    def l10n_br_sst_gerar_aso_retorno(self, dias_afastado, data_retorno=None):
        """Gera o ASO de retorno ao trabalho quando o afastamento passa de 30 dias.

        Fica como método público porque o gatilho do afastamento muda conforme a
        instalação: pode vir das férias e licenças, do acidente de trabalho ou
        do próprio S-2230.
        """
        self.ensure_one()
        if dias_afastado < DIAS_AFASTAMENTO_RETORNO:
            return self.env["hr.employee.medical.examination"]
        return self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self, TIPO_ASO_RETORNO, date=data_retorno
        )
