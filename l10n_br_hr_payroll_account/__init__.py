# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import models


def post_init_hook(env):
    """Vincula regras salariais BR ao plano de contas e configura o FOPAG.

    Entrega a contabilização funcional out-of-the-box para as empresas que já
    possuem plano de contas no momento da instalação. É idempotente e pode ser
    reexecutado sem sobrescrever configuração manual.
    """
    env["hr.salary.rule"]._l10n_br_setup_payroll_accounts()
