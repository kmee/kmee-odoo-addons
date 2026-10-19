# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, company):
        """Após aplicar um plano de contas, (re)tenta o mapeamento FOPAG.

        A auto-instalação dos módulos de plano de contas (l10n_generic_coa,
        l10n_br_coa_*) pode ocorrer DEPOIS deste módulo; nesse caso o
        ``post_init_hook`` roda cedo demais (sem contas). Este gancho garante
        que, assim que um CoA é aplicado, as regras salariais BR e o diário
        FOPAG sejam vinculados. A rotina é idempotente e mira a empresa dona do
        diário FOPAG (ver ``hr.salary.rule._l10n_br_setup_payroll_accounts``).
        """
        res = super()._load(company)
        self.env["hr.salary.rule"]._l10n_br_setup_payroll_accounts()
        return res
