# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMappingPlan(models.Model):
    _inherit = "l10n_br_account_mapping.plan"

    sped_referential = fields.Boolean(
        string="Plano referencial da RFB",
        help="Marque quando este plano de destino representar um plano "
        "referencial da Receita Federal. E o mapeamento que alimenta o "
        "registro I051 do SPED Contabil (ECD).",
    )
    sped_layout_version = fields.Char(
        string="Leiaute de origem",
        help="Versao do leiaute da tabela dinamica da RFB de onde este plano "
        "foi carregado (auditoria da carga).",
    )
    sped_plan_code = fields.Char(
        string="Codigo do plano referencial",
        size=10,
        help="Codigo do plano na tabela de planos referenciais da RFB "
        "(campo COD_PLAN_REF do registro I051 da ECD). Exemplos da tabela "
        "oficial: 1 para PJ em geral do Lucro Real, 2 para PJ em geral do "
        "Lucro Presumido. Consulte a tabela dinamica do SPED vigente no ano "
        "da escrituracao.",
    )

    @api.constrains("sped_referential", "sped_plan_code")
    def _check_sped_plan_code(self):
        for plan in self:
            if plan.sped_referential and not plan.sped_plan_code:
                raise ValidationError(
                    _(
                        "O plano %s esta marcado como referencial da RFB e "
                        "precisa do codigo do plano (COD_PLAN_REF)."
                    )
                    % plan.name
                )

    def sped_referential_line(self, account, date=None):
        """Dados do registro I051 da ECD para uma conta do Odoo.

        Devolve ``{"COD_PLAN_REF": ..., "COD_CTA_REF": ...}`` quando a conta
        esta mapeada neste plano, ou ``{}`` quando nao esta. O I051 e opcional
        por conta na ECD: conta sem mapeamento simplesmente nao gera o
        registro filho.

        :param date: data-base da escrituracao; escrituracao retificadora de
            ano anterior usa a tabela vigente na epoca.
        """
        self.ensure_one()
        dest = self.resolve(account, date=date)
        if not dest:
            return {}
        return {
            "COD_PLAN_REF": self.sped_plan_code or "",
            "COD_CTA_REF": dest.code,
        }


class AccountMappingAccount(models.Model):
    _inherit = "l10n_br_account_mapping.account"

    sped_account_type = fields.Selection(
        [("S", "Sintetica"), ("A", "Analitica")],
        string="Tipo (RFB)",
        help="Tipo da conta na tabela referencial: sintetica (agrupadora) ou "
        "analitica (recebe mapeamento). O I051 so referencia analiticas.",
    )
    sped_parent_code = fields.Char(
        string="Conta superior (RFB)",
        size=20,
        help="Codigo da conta superior na hierarquia da tabela referencial.",
    )
    sped_nature = fields.Char(
        string="Natureza (RFB)",
        size=2,
        help="Natureza da conta na tabela referencial (1 ativo, 2 passivo, "
        "3 patrimonio liquido, 4 resultado, 9 outras).",
    )
    sped_level = fields.Integer(
        string="Nivel (RFB)",
        help="Nivel da conta na hierarquia da tabela referencial (coluna "
        "NIVEL da tabela dinamica). Os registros P100/P150 da ECF e o E010 "
        "exigem o nivel oficial, que nem sempre e a profundidade do codigo.",
    )
