# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import os

from odoo import models

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = "ir.cron"

    @classmethod
    def _process_job(cls, db, cron_cr, job):
        if os.getenv("DISABLE_CRON_DURING_UPDATE"):
            # Skip all cron processing
            _logger.info(
                "DISABLE_CRON_DURING_UPDATE is set, skipping cron jobs processing"
            )
            return
        return super()._process_job(db, cron_cr, job)

    @classmethod
    def _process_jobs(cls, db_name):
        if os.getenv("DISABLE_CRON_DURING_UPDATE"):
            # Skip all cron processing
            _logger.info(
                "DISABLE_CRON_DURING_UPDATE is set, skipping cron jobs processing"
            )
            return
        return super()._process_jobs(db_name)
