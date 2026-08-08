# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def l10n_br_sped_referential_line(self):
        """Dados do I051 desta conta, pelo plano referencial da empresa.

        E o ponto de consumo do gerador da ECD: para cada conta do I050, se
        este metodo devolver dados, o I051 e emitido como filho.
        """
        self.ensure_one()
        plan = self.company_id.l10n_br_sped_referential_plan_id
        if not plan:
            return {}
        return plan.sped_referential_line(self)
