# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _l10n_br_payroll_journal(self):
        """Retorna o diário de folha (FOPAG) da empresa ativa.

        O default do OCA ``payroll_account`` para ``journal_id`` do holerite é o
        primeiro diário do tipo ``general`` da base, que em qualquer base com
        plano de contas genérico é o "Miscellaneous Operations" — um diário que
        ninguém configurou para folha. Como este módulo entrega o FOPAG já
        mapeado (``default_account_id`` mais as contas nas regras salariais),
        o holerite precisa nascer nele: no diário genérico o
        ``action_payslip_done`` falha ao procurar a conta de contrapartida
        ('The Expense Journal "..." has not properly configured the Credit
        Account!').

        Cai no comportamento original (primeiro diário ``general`` da empresa)
        quando o FOPAG não existe.
        """
        company = self.env.company
        journal = self.env.ref(
            "l10n_br_hr_payroll_account.journal_folha_pagamento",
            raise_if_not_found=False,
        )
        if journal and journal.company_id in (company, False):
            return journal
        journal = self.search(
            [("code", "=", "FOPAG"), ("company_id", "=", company.id)], limit=1
        )
        if journal:
            return journal
        return self.search(
            [("type", "=", "general"), ("company_id", "=", company.id)], limit=1
        )
