# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # O default do OCA é o primeiro diário `general` da base ("Miscellaneous
    # Operations" em bases com CoA genérico), que não tem conta de
    # contrapartida configurada e faz o action_payslip_done falhar agora que
    # este módulo entrega o mapeamento regra→conta. Ver _l10n_br_payroll_journal.
    journal_id = fields.Many2one(
        default=lambda self: self.env["account.journal"]._l10n_br_payroll_journal()
    )

    @api.model
    def _demo_compute_payslips(self):
        """Pin every demo payslip to the Folha de Pagamento journal (FOPAG).

        Bug 2 (demo) had two coupled causes:

        1) The demo payslips are declared in modules that do NOT depend on
           ``account`` (``l10n_br_hr_payroll`` and ``l10n_br_hr_vacation``), so
           their ``journal_id`` comes from the OCA default
           ``search([('type', '=', 'general')], limit=1)`` -- the first general
           journal, which is FOPAG (id=1). Payslips created before
           ``payroll_account`` added the column keep ``journal_id`` NULL.
        2) In demo mode the company's chart of accounts (``l10n_generic_coa``)
           is loaded last, via ``account.chart.template._load``. Because the
           company already had accounts (the illustrative ones from this
           module's ``demo/account_demo.xml``), ``_load`` treated it as a
           localization switch and DELETED every company journal -- including
           FOPAG -- before recreating the chart, orphaning
           ``hr_payslip_journal_id_fkey`` -> ForeignKeyViolation.

        The destructive wipe is neutralized by dropping those unused demo
        accounts (see ``demo/account_demo.xml``), so FOPAG survives the chart
        load. This override -- the single choke point, called from the vacation
        demo after every demo payslip exists and after this account-aware module
        is loaded -- additionally normalizes any payslip still on a NULL/other
        journal to FOPAG, so the demo consistently uses one payroll journal
        regardless of module load order.
        """
        journal = self.env.ref(
            "l10n_br_hr_payroll_account.journal_folha_pagamento",
            raise_if_not_found=False,
        )
        if journal:
            slips = self.search([("state", "=", "draft")])
            to_fix = slips.filtered(lambda s: s.journal_id != journal)
            if to_fix:
                to_fix.write({"journal_id": journal.id})
                _logger.info(
                    "Demo: %d holerites vinculados ao diário FOPAG", len(to_fix)
                )
        return super()._demo_compute_payslips()
