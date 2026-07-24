# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Regras salariais BR (l10n_br_hr_payroll) e como cada uma é contabilizada.
# O valor indica em qual lado o débito/crédito deve cair, resolvido a partir
# do plano de contas JÁ CARREGADO na empresa (nunca criamos contas próprias —
# ver a restrição de bug do CoA em demo/account_demo.xml).
#   - "expense"   -> conta de despesa (débito)
#   - "liability" -> conta de passivo circulante / a pagar (crédito)
_RULE_ACCOUNT_MAP = {
    "l10n_br_hr_payroll.hr_rule_salario_base": {"debit": "expense"},
    "l10n_br_hr_payroll.hr_rule_inss": {"credit": "liability"},
    "l10n_br_hr_payroll.hr_rule_irrf": {"credit": "liability"},
    "l10n_br_hr_payroll.hr_rule_fgts": {"debit": "expense", "credit": "liability"},
    "l10n_br_hr_payroll.hr_rule_net": {"credit": "liability"},
}


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    @api.model
    def _l10n_br_find_account(self, company, kind):
        """Localiza uma conta contábil da empresa por tipo lógico.

        Usa apenas contas do plano de contas vigente da empresa (não cria
        contas). Retorna ``account.account`` ou registro vazio.
        """
        Account = self.env["account.account"]
        if kind == "expense":
            types = ["expense"]
        else:  # liability
            types = ["liability_current", "liability_payable", "liability_non_current"]
        for account_type in types:
            account = Account.search(
                [
                    ("account_type", "=", account_type),
                    ("company_id", "=", company.id),
                    ("deprecated", "=", False),
                ],
                order="code",
                limit=1,
            )
            if account:
                return account
        return Account

    @api.model
    def _l10n_br_setup_payroll_accounts(self, company=None):
        """Configura o mapeamento regra→conta e o diário FOPAG.

        Entrega uma contabilização funcional out-of-the-box: vincula as regras
        salariais BR a contas de despesa/passivo do plano de contas vigente e
        define a ``default_account_id``/``company_id`` do diário Folha de
        Pagamento (usado pelo OCA ``payroll_account`` para balancear o
        lançamento).

        O vínculo é feito para uma ÚNICA empresa — a dona do diário FOPAG (ou a
        empresa principal), pois ``hr.salary.rule.account_debit``/
        ``account_credit`` são campos independentes de empresa; apontar as
        regras para contas de empresas diferentes geraria erro de empresa
        cruzada ao lançar o holerite. Cenários multiempresa devem configurar as
        contas manualmente por empresa.

        Chamado tanto no ``post_init_hook`` (quando o CoA já existe) quanto ao
        carregar um plano de contas (``account.chart.template._load``), porque a
        ordem de instalação pode aplicar o CoA depois deste módulo.

        Idempotente e não-destrutivo:
          - só preenche campos ainda vazios (respeita configuração manual);
          - não cria contas contábeis (evita o wipe do CoA em modo demo).
        """
        journal = self.env.ref(
            "l10n_br_hr_payroll_account.journal_folha_pagamento",
            raise_if_not_found=False,
        )
        if company is None:
            company = (
                (journal.company_id if journal and journal.company_id else False)
                or self.env.ref("base.main_company", raise_if_not_found=False)
                or self.env.company
            )

        expense = self._l10n_br_find_account(company, "expense")
        liability = self._l10n_br_find_account(company, "liability")
        if not expense or not liability:
            _logger.info(
                "FOPAG: empresa %s sem plano de contas suficiente; "
                "mapeamento regra→conta adiado.",
                company.display_name,
            )
            return False

        accounts = {"expense": expense, "liability": liability}
        for xmlid, sides in _RULE_ACCOUNT_MAP.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if not rule:
                continue
            vals = {}
            if "debit" in sides and not rule.account_debit:
                vals["account_debit"] = accounts[sides["debit"]].id
            if "credit" in sides and not rule.account_credit:
                vals["account_credit"] = accounts[sides["credit"]].id
            if vals:
                rule.write(vals)

        # Diário FOPAG: garante conta padrão (conta de balanceamento) e empresa.
        if journal and (not journal.company_id or journal.company_id == company):
            jvals = {}
            if not journal.company_id:
                jvals["company_id"] = company.id
            if not journal.default_account_id:
                jvals["default_account_id"] = liability.id
            if jvals:
                journal.write(jvals)

        _logger.info(
            "FOPAG: mapeamento regra→conta aplicado para a empresa %s.",
            company.display_name,
        )
        return True
