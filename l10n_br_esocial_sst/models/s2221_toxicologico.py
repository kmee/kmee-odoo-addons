# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# codSeqExame: duas letras seguidas de nove dígitos.
RE_COD_SEQ_EXAME = re.compile(r"^[A-Z]{2}\d{9}$")


class ESocialS2221(models.Model):
    """S-2221 - Exame Toxicológico do Motorista Profissional (Lei 13.103/2015).

    Obrigatório para motorista profissional das categorias C, D e E. O prazo é
    o dia 15 do mês seguinte ao exame; no pré-admissional, o dia 15 do mês
    seguinte ao da admissão.
    """

    _name = "l10n_br.esocial.s2221"
    _inherit = "l10n_br.esocial.base.sst"
    _description = "eSocial S-2221 - Exame Toxicológico do Motorista"
    _order = "dt_exame desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    dt_exame = fields.Date(
        string="Data do Exame",
        required=True,
        default=fields.Date.context_today,
    )
    cnpj_lab = fields.Char(
        string="CNPJ do Laboratório",
        size=18,
        required=True,
    )
    cod_seq_exame = fields.Char(
        string="Código do Exame",
        size=11,
        required=True,
        help="Código sequencial do exame toxicológico: duas letras seguidas "
        "de nove dígitos.",
    )
    nm_med = fields.Char(
        string="Médico Responsável",
        required=True,
    )
    nr_crm = fields.Char(string="CRM")
    uf_crm = fields.Char(string="UF do CRM", size=2)

    @api.depends("employee_id", "dt_exame")
    def _compute_name(self):
        for rec in self:
            partes = [rec.employee_id.name, rec.dt_exame and str(rec.dt_exame)]
            rec.name = " - ".join(p for p in partes if p)

    @api.constrains("cnpj_lab")
    def _check_cnpj_lab(self):
        for rec in self:
            if len(rec._so_digitos(rec.cnpj_lab)) != 14:
                raise ValidationError(_("CNPJ do laboratório deve ter 14 dígitos."))

    @api.constrains("cod_seq_exame")
    def _check_cod_seq_exame(self):
        for rec in self:
            if not RE_COD_SEQ_EXAME.match((rec.cod_seq_exame or "").upper()):
                raise ValidationError(
                    _(
                        "Código do exame inválido: %(valor)r. O eSocial espera "
                        "duas letras seguidas de nove dígitos, por exemplo "
                        "AB123456789."
                    )
                    % {"valor": rec.cod_seq_exame}
                )

    def _get_event_type(self):
        return "S-2221"

    def _to_esociallib_dict(self):
        self.ensure_one()
        if not self.employee_id.l10n_br_esocial_matricula:
            raise UserError(
                _("S-2221 de %(nome)s: o evento exige a matrícula do " "trabalhador.")
                % {"nome": self.employee_id.name}
            )
        dados = self._get_dados_comuns()
        dados.update(
            {
                "dt_exame": str(self.dt_exame),
                "cnpj_lab": self._so_digitos(self.cnpj_lab),
                "cod_seq_exame": self.cod_seq_exame.upper(),
                "nm_med": self.nm_med,
            }
        )
        if self.nr_crm:
            dados["nr_crm"] = self.nr_crm
        if self.uf_crm:
            dados["uf_crm"] = self.uf_crm.upper()
        return dados
