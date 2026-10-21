# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Reescreve a regra do adicional de GILRAT nas bases já instaladas.

O XML da regra é ``noupdate``: sem esta migração, quem já tinha o módulo
continuaria calculando o adicional pelos riscos de hoje, e não pelos do
período do holerite. Regra alterada à mão pelo cliente não é tocada.
"""

from odoo import SUPERUSER_ID, api

# Script de migração é carregado pelo caminho do arquivo, fora do pacote do
# módulo: o import relativo não funciona aqui.
# pylint: disable=odoo-addons-relative-import
from odoo.addons.l10n_br_hr_payroll_sst.models.hr_contract import (
    REGRA_GILRAT_CONDICAO,
    REGRA_GILRAT_VALOR,
)

CONDICAO_ANTERIOR = "result = contract.l10n_br_sst_aliquota_gilrat > 0"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    regra = env.ref(
        "l10n_br_hr_payroll_sst.hr_rule_gilrat_adicional", raise_if_not_found=False
    )
    if not regra or (regra.condition_python or "").strip() != CONDICAO_ANTERIOR:
        return
    regra.write(
        {
            "condition_python": REGRA_GILRAT_CONDICAO,
            "amount_python_compute": REGRA_GILRAT_VALOR,
        }
    )
