# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    # Na 17.0 o diario do holerite e related ao do contrato (payroll_account).
    # O default vai aqui: o contrato nasce no diario de folha (FOPAG) em vez do
    # primeiro diario `general` da base (ver account.journal._l10n_br_payroll_journal).
    journal_id = fields.Many2one(
        default=lambda self: self.env["account.journal"]._l10n_br_payroll_journal()
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Corrige o diário quando o contrato é de OUTRA empresa.

        O default de ``journal_id`` é avaliado com a empresa ATIVA, mas o
        contrato pode nascer com ``company_id`` de outra empresa (folha
        multiempresa, demo por regime tributário, criação via API). Como o
        diário do holerite vem do contrato, sem esta correção o lançamento
        contábil de uma empresa iria para o diário de outra, em silêncio.

        Se a empresa do contrato não tiver diário de folha, o diário original é
        mantido: a contabilização fica a cargo de quem configurar o diário
        daquela empresa.
        """
        contracts = super().create(vals_list)
        Journal = self.env["account.journal"]
        for contract in contracts:
            journal_company = contract.journal_id.company_id
            if not contract.company_id or journal_company in (
                contract.company_id,
                False,
            ):
                continue
            journal = Journal.with_company(
                contract.company_id
            )._l10n_br_payroll_journal()
            if journal and journal.company_id in (contract.company_id, False):
                contract.journal_id = journal
        return contracts
