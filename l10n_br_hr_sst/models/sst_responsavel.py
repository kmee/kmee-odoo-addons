# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .sst_dominios import IDE_ORGAO_CLASSE_RESP


class L10nBrSstResponsavel(models.Model):
    """Responsável pelos registros ambientais (grupo respReg do S-2240).

    É o profissional legalmente habilitado que assina o laudo: médico do
    trabalho (CRM), engenheiro de segurança (CREA) ou outro conselho. O grupo
    respReg é obrigatório no S-2240, então sem este cadastro o evento não sai.
    """

    _name = "l10n_br.sst.responsavel"
    _description = "SST - Responsável pelos Registros Ambientais"
    _order = "name"

    name = fields.Char(
        string="Nome",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Parceiro",
        help="Opcional. Liga o responsável a um cadastro de parceiro.",
    )
    cpf = fields.Char(
        string="CPF",
        size=14,
        required=True,
        help="CPF do responsável, informado no campo cpfResp do S-2240.",
    )
    ide_oc = fields.Selection(
        IDE_ORGAO_CLASSE_RESP,
        string="Órgão de Classe",
    )
    dsc_oc = fields.Char(
        string="Descrição do Órgão de Classe",
        help="Obrigatório quando o órgão de classe é 'Outros'.",
    )
    nr_oc = fields.Char(
        string="Número de Inscrição no Órgão",
    )
    uf_oc = fields.Char(
        string="UF do Órgão de Classe",
        size=2,
    )
    active = fields.Boolean(default=True)

    @api.constrains("cpf")
    def _check_cpf(self):
        for rec in self:
            digitos = "".join(c for c in (rec.cpf or "") if c.isdigit())
            if len(digitos) != 11:
                raise ValidationError(
                    _("CPF do responsável %(nome)s deve ter 11 dígitos.")
                    % {"nome": rec.name}
                )

    @api.constrains("ide_oc", "dsc_oc")
    def _check_dsc_oc(self):
        for rec in self:
            if rec.ide_oc == "9" and not rec.dsc_oc:
                raise ValidationError(
                    _(
                        "Responsável %(nome)s: informe a descrição do órgão de "
                        "classe quando o órgão é 'Outros'."
                    )
                    % {"nome": rec.name}
                )

    def _to_resp_reg(self):
        """Dicionário do grupo respReg consumido pelo intermediário S-2240."""
        self.ensure_one()
        dados = {
            "cpf_resp": "".join(c for c in (self.cpf or "") if c.isdigit()),
        }
        if self.ide_oc:
            dados["ide_oc"] = int(self.ide_oc)
        if self.dsc_oc:
            dados["dsc_oc"] = self.dsc_oc
        if self.nr_oc:
            dados["nr_oc"] = self.nr_oc
        if self.uf_oc:
            dados["uf_oc"] = self.uf_oc.upper()
        return dados
