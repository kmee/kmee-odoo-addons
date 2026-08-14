# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# A regra de líquido do l10n_br_hr_payroll soma apenas BASIC e ALW. Verba
# indenizatória (categoria IND) precisa entrar no líquido SEM entrar no bruto,
# porque é justamente o bruto que serve de base a INSS e IRRF.
FORMULA_NET = (
    "result = categories.BASIC + categories.ALW + categories.IND - categories.DED"
)

REGRAS_NOVAS = (
    "l10n_br_hr_payroll_attendance.hr_rule_dsr_he",
    "l10n_br_hr_payroll_attendance.hr_rule_intervalo_suprimido",
)


def post_init_hook(cr, registry):
    """Liga as rubricas de jornada à estrutura CLT e ao líquido.

    Os dados do ``l10n_br_hr_payroll`` são ``noupdate="1"``, então a estrutura
    e a regra de líquido não podem ser alteradas por XML de outro módulo. O
    ajuste vai por código, é idempotente e registra o que fez.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _adiciona_regras_a_estrutura(env)
    _inclui_indenizatorias_no_liquido(env)


def _adiciona_regras_a_estrutura(env):
    estrutura = env.ref("l10n_br_hr_payroll.structure_clt", raise_if_not_found=False)
    if not estrutura:
        _logger.warning(
            "Estrutura CLT não encontrada: as rubricas de jornada precisam ser "
            "vinculadas manualmente."
        )
        return
    novas = [env.ref(xmlid, raise_if_not_found=False) for xmlid in REGRAS_NOVAS]
    faltantes = [
        regra.id for regra in novas if regra and regra not in estrutura.rule_ids
    ]
    if faltantes:
        estrutura.write({"rule_ids": [(4, regra_id) for regra_id in faltantes]})
        _logger.info(
            "Estrutura CLT: %d rubrica(s) de jornada vinculada(s).", len(faltantes)
        )


def _inclui_indenizatorias_no_liquido(env):
    regra_net = env.ref("l10n_br_hr_payroll.hr_rule_net", raise_if_not_found=False)
    if not regra_net:
        return
    if "categories.IND" in (regra_net.amount_python_compute or ""):
        return
    regra_net.write({"amount_python_compute": FORMULA_NET})
    _logger.info("Regra NET ajustada para somar verbas indenizatórias (categoria IND).")
