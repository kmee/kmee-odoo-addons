# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMappingPlan(models.Model):
    _inherit = "l10n_br.account.mapping.plan"

    sped_referential = fields.Boolean(
        string="Plano referencial da RFB",
        help="Marque quando este plano de destino representar um plano "
        "referencial da Receita Federal. E o mapeamento que alimenta o "
        "registro I051 do SPED Contabil (ECD).",
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

    def sped_referential_line(self, account):
        """Dados do registro I051 da ECD para uma conta do Odoo.

        Devolve ``{"COD_PLAN_REF": ..., "COD_CTA_REF": ...}`` quando a conta
        esta mapeada neste plano, ou ``{}`` quando nao esta. O I051 e opcional
        por conta na ECD: conta sem mapeamento simplesmente nao gera o
        registro filho.
        """
        self.ensure_one()
        dest = self.resolve(account)
        if not dest:
            return {}
        return {
            "COD_PLAN_REF": self.sped_plan_code or "",
            "COD_CTA_REF": dest.code,
        }
