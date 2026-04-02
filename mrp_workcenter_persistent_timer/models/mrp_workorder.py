# Copyright (C) 2025-Today - KMEE (https://www.kmee.com.br).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def action_back_no_pause(self):
        """Leave tablet view without pausing the workorder timer.

        Temporarily set working_state to 'blocked' so that action_back()
        does not call button_pending() (which would pause the workcenter timer).
        Restore the previous working_state after navigation.
        """
        self.ensure_one()
        backup_working_state = self.working_state
        self.working_state = "blocked"
        action = self.action_back()
        self.working_state = backup_working_state
        return action
