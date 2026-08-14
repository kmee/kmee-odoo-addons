# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError

from .hr_employee_medical_examination import TIPO_ASO_ADMISSIONAL, TIPO_ASO_DEMISSIONAL


class HrContract(models.Model):
    _inherit = "hr.contract"

    def _l10n_br_sst_exige_aso(self, tipo_codigo):
        """Verifica o ASO exigido e aplica a política da empresa.

        A NR-7 exige o exame admissional antes do início do trabalho e o
        demissional na rescisão. Empresa que ainda não tem o processo redondo
        pode se contentar com o alerta, e é esse o padrão: bloquear a admissão
        de quem já foi contratado costuma travar a folha, não proteger ninguém.
        """
        self.ensure_one()
        politica = self.company_id.l10n_br_sst_aso_politica
        if politica == "ignora":
            return True
        exame = self.env["hr.employee.medical.examination"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("l10n_br_tipo_aso_codigo", "=", tipo_codigo),
                ("state", "=", "done"),
            ],
            limit=1,
        )
        if exame:
            return True
        rotulos = {
            TIPO_ASO_ADMISSIONAL: _("admissional"),
            TIPO_ASO_DEMISSIONAL: _("demissional"),
        }
        mensagem = _(
            "O trabalhador %(nome)s não tem ASO %(tipo)s concluído, exigido "
            "pela NR-7."
        ) % {
            "nome": self.employee_id.name,
            "tipo": rotulos.get(tipo_codigo, tipo_codigo),
        }
        if politica == "bloqueia":
            raise UserError(mensagem)
        self.message_post(body=mensagem)
        return False

    def write(self, vals):
        """Checa o ASO nas duas pontas do vínculo: admissão e rescisão."""
        res = super().write(vals)
        if vals.get("state") == "open":
            for rec in self:
                rec._l10n_br_sst_exige_aso(TIPO_ASO_ADMISSIONAL)
        elif vals.get("state") == "close":
            for rec in self:
                rec._l10n_br_sst_exige_aso(TIPO_ASO_DEMISSIONAL)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        for contract in contracts.filtered(lambda c: c.state == "open"):
            contract._l10n_br_sst_exige_aso(TIPO_ASO_ADMISSIONAL)
        return contracts
