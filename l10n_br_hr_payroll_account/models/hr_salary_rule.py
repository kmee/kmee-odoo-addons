# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Contas lógicas ("slots") usadas pelo mapeamento regra->conta.
#
# Cada slot declara os TIPOS de conta aceitáveis e uma lista de palavras-chave
# tentadas na ordem. A conta é sempre buscada no plano de contas JÁ CARREGADO
# na empresa - este módulo nunca cria contas (ver a restrição de bug do CoA em
# demo/account_demo.xml). Quando nenhuma palavra-chave casa, cai na primeira
# conta do tipo, que é o comportamento anterior: num plano genérico em inglês
# tudo continua caindo numa despesa e num passivo, e num plano brasileiro
# (l10n_br_coa_generic) cada tributo encontra a sua conta ("INSS a Recolher",
# "FGTS a Recolher", "Férias a Pagar", "Encargos Sociais"...).
_LIABILITY_TYPES = ("liability_current", "liability_payable", "liability_non_current")
_ACCOUNT_SLOTS = {
    # Genéricos (compatibilidade com o mapeamento anterior).
    "expense": (("expense",), ()),
    "liability": (_LIABILITY_TYPES, ()),
    # Despesas
    "expense_salarios": (("expense",), ("Salário", "Salario", "Ordenado")),
    "expense_encargos": (("expense",), ("Encargos", "Previd", "INSS", "FGTS")),
    "expense_provisao_ferias": (("expense",), ("Provis", "Férias", "Ferias")),
    "expense_provisao_13": (("expense",), ("Provis", "13")),
    # Passivos
    "liability_salarios": (_LIABILITY_TYPES, ("Salário", "Salario")),
    "liability_inss": (_LIABILITY_TYPES, ("INSS", "Previd")),
    "liability_irrf": (_LIABILITY_TYPES, ("IRRF", "Imposto de Renda")),
    "liability_fgts": (_LIABILITY_TYPES, ("FGTS",)),
    # Terceiros: recolhidos na mesma guia previdenciária, daí o INSS como
    # segunda opção quando não há conta própria de outras entidades.
    "liability_terceiros": (
        _LIABILITY_TYPES,
        ("Terceiros", "Outras Entidades", "INSS"),
    ),
    "liability_ferias": (_LIABILITY_TYPES, ("Férias", "Ferias")),
    "liability_13": (_LIABILITY_TYPES, ("13", "Décimo", "Decimo")),
}

# Regras salariais BR (l10n_br_hr_payroll) e como cada uma é contabilizada:
# em que slot cai o débito e em que slot cai o crédito.
#
# Encargo patronal tem SEMPRE os dois lados (despesa de encargos x tributo a
# recolher) - é custo do empregador, não desconto do empregado, e por isso não
# aparece no líquido mas precisa aparecer no resultado. As provisões seguem a
# mesma lógica (despesa de provisão x provisão a pagar), reconhecendo por
# competência o que só será desembolsado depois.
_RULE_ACCOUNT_MAP = {
    "l10n_br_hr_payroll.hr_rule_salario_base": {"debit": "expense_salarios"},
    "l10n_br_hr_payroll.hr_rule_inss": {"credit": "liability_inss"},
    "l10n_br_hr_payroll.hr_rule_irrf": {"credit": "liability_irrf"},
    "l10n_br_hr_payroll.hr_rule_fgts": {
        "debit": "expense_encargos",
        "credit": "liability_fgts",
    },
    "l10n_br_hr_payroll.hr_rule_fgts_aprendiz": {
        "debit": "expense_encargos",
        "credit": "liability_fgts",
    },
    # Encargos patronais previdenciários (RF-31/RF-32/RF-33)
    "l10n_br_hr_payroll.hr_rule_cpp_patronal": {
        "debit": "expense_encargos",
        "credit": "liability_inss",
    },
    "l10n_br_hr_payroll.hr_rule_rat_patronal": {
        "debit": "expense_encargos",
        "credit": "liability_inss",
    },
    "l10n_br_hr_payroll.hr_rule_terceiros_patronal": {
        "debit": "expense_encargos",
        "credit": "liability_terceiros",
    },
    # Provisões de férias e 13º com encargos (RF-34)
    "l10n_br_hr_payroll.hr_rule_provisao_ferias": {
        "debit": "expense_provisao_ferias",
        "credit": "liability_ferias",
    },
    "l10n_br_hr_payroll.hr_rule_provisao_ferias_encargos": {
        "debit": "expense_provisao_ferias",
        "credit": "liability_ferias",
    },
    "l10n_br_hr_payroll.hr_rule_provisao_decimo": {
        "debit": "expense_provisao_13",
        "credit": "liability_13",
    },
    "l10n_br_hr_payroll.hr_rule_provisao_decimo_encargos": {
        "debit": "expense_provisao_13",
        "credit": "liability_13",
    },
    "l10n_br_hr_payroll.hr_rule_net": {"credit": "liability_salarios"},
}


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    @api.model
    def _l10n_br_find_account(self, company, kind):
        """Localiza uma conta contábil da empresa pelo slot lógico ``kind``.

        Usa apenas contas do plano de contas vigente da empresa (não cria
        contas). A busca é feita em duas etapas:

          1. por palavra-chave do slot (ex.: "FGTS", "Férias"), dentro dos
             tipos aceitos - é o que faz cada tributo cair na sua conta num
             plano de contas brasileiro;
          2. sem palavra-chave, a primeira conta do tipo (comportamento
             anterior), para que planos genéricos continuem funcionando.

        Em ambos os casos a ordem é por código, o que torna a escolha
        determinística (e não dependente da ordem de criação).

        Returns:
            ``account.account`` encontrado ou recordset vazio.
        """
        Account = self.env["account.account"]
        types, keywords = _ACCOUNT_SLOTS.get(kind, _ACCOUNT_SLOTS["liability"])
        base_domain = [
            ("account_type", "in", list(types)),
            ("company_id", "=", company.id),
            ("deprecated", "=", False),
        ]
        for keyword in keywords:
            account = Account.search(
                base_domain + [("name", "ilike", keyword)], order="code", limit=1
            )
            if account:
                return account
        # Fallback: respeita a ordem dos tipos declarada no slot.
        for account_type in types:
            account = Account.search(
                [("account_type", "=", account_type)] + base_domain[1:],
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

        # Um slot é resolvido uma única vez por empresa (várias regras
        # compartilham o mesmo slot, ex.: todos os encargos patronais debitam
        # despesa de encargos sociais).
        accounts = {}
        for xmlid, sides in _RULE_ACCOUNT_MAP.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if not rule:
                continue
            vals = {}
            for side, field in (
                ("debit", "account_debit"),
                ("credit", "account_credit"),
            ):
                slot = sides.get(side)
                if not slot or rule[field]:
                    continue
                if slot not in accounts:
                    accounts[slot] = self._l10n_br_find_account(company, slot)
                if accounts[slot]:
                    vals[field] = accounts[slot].id
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
