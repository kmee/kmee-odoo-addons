# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ESocialS2220(models.Model):
    """S-2220 - Monitoramento da Saúde do Trabalhador (ASO).

    Prazo de envio: até o dia 15 do mês seguinte ao do exame. O evento leva o
    ASO, e não o prontuário: diagnóstico é sigilo médico e não sai daqui.
    """

    _name = "l10n_br.esocial.s2220"
    _inherit = "l10n_br.esocial.base.sst"
    _description = "eSocial S-2220 - Monitoramento da Saúde do Trabalhador"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    examination_id = fields.Many2one(
        "hr.employee.medical.examination",
        string="ASO",
        required=True,
        ondelete="cascade",
    )
    dt_aso = fields.Date(
        related="examination_id.date",
        string="Data do ASO",
        store=True,
        readonly=True,
    )

    @api.depends("examination_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.examination_id.display_name

    def _get_event_type(self):
        return "S-2220"

    def _validar_antes_do_envio(self):
        for rec in self:
            exame = rec.examination_id
            faltando = []
            if not exame.l10n_br_tipo_aso_id:
                faltando.append(_("tipo de ASO"))
            if not exame.date:
                faltando.append(_("data do ASO"))
            if not exame.l10n_br_medico_nome:
                faltando.append(_("nome do médico emitente"))
            if not exame.l10n_br_exame_ids:
                faltando.append(_("ao menos um exame complementar"))
            if faltando:
                raise UserError(
                    _("S-2220 de %(nome)s: informe %(campos)s antes de " "transmitir.")
                    % {
                        "nome": rec.employee_id.name,
                        "campos": ", ".join(faltando),
                    }
                )

    def action_gerar_evento(self):
        self._validar_antes_do_envio()
        return super().action_gerar_evento()

    def _to_esociallib_dict(self):
        self.ensure_one()
        self._validar_antes_do_envio()
        exame = self.examination_id
        dados = self._get_dados_comuns()
        dados.update(
            {
                "tp_exame_ocup": int(exame.l10n_br_tipo_aso_codigo),
                "dt_aso": str(exame.date),
                "exames": [linha._to_exame() for linha in exame.l10n_br_exame_ids],
                "nm_med": exame.l10n_br_medico_nome,
            }
        )
        if exame.l10n_br_resultado:
            dados["res_aso"] = int(exame.l10n_br_resultado)
        if exame.l10n_br_crm:
            dados["nr_crm"] = exame.l10n_br_crm
        if exame.l10n_br_uf_crm:
            dados["uf_crm"] = exame.l10n_br_uf_crm.upper()
        coordenador = exame.l10n_br_pcmso_id.medico_coordenador_id
        if coordenador:
            dados["cpf_resp"] = self._so_digitos(coordenador.cpf)
            dados["nm_resp"] = coordenador.name
            if coordenador.nr_oc:
                dados["nr_crm_resp"] = coordenador.nr_oc
            if coordenador.uf_oc:
                dados["uf_crm_resp"] = coordenador.uf_oc.upper()
        return dados

    @api.model
    def gerar_para_exame(self, exame):
        """Cria o S-2220 do ASO informado, sem duplicar evento já gerado."""
        exame.ensure_one()
        existente = self.search(
            [("examination_id", "=", exame.id), ("ind_retif", "=", "1")], limit=1
        )
        if existente:
            return existente
        return self.create(
            {
                "company_id": (exame.employee_id.company_id or self.env.company).id,
                "employee_id": exame.employee_id.id,
                "examination_id": exame.id,
            }
        )
