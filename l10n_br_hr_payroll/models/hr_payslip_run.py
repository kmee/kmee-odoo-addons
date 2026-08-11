# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    @api.model
    def _demo_confirm_runs(self, run_ids):
        """Confirm demo payslip batches: confirm every slip and close the batch.

        Called from demo XML via ``<function>``. Demo data must reproduce the
        FULL life cycle -- a batch left in draft with uncomputed payslips shows
        empty screens, which is exactly what a commercial demo must not do.

        ``action_payslip_done`` recomputes the payslip before confirming (OCA
        behaviour), so calling this on already-computed slips is safe and
        idempotent: slips already in ``done`` are skipped.

        Args:
            run_ids: ids of the ``hr.payslip.run`` records to confirm.
        """
        runs = self.browse(run_ids).exists()
        for run in runs:
            slips = run.slip_ids.filtered(lambda s: s.state not in ("done", "cancel"))
            for slip in slips:
                try:
                    slip.action_payslip_done()
                except Exception:
                    _logger.warning(
                        "Demo: falha ao confirmar holerite %s", slip.name, exc_info=True
                    )
            run.close_payslip_run()
            _logger.info(
                "Demo: lote %s fechado com %d holerites confirmados",
                run.name,
                len(run.slip_ids.filtered(lambda s: s.state == "done")),
            )
        return True
