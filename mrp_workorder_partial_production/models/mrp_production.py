# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _check_tracked_components_have_lot(self):
        self.ensure_one()
        missing = self.move_raw_ids.filtered(
            lambda m: m.product_id.tracking != "none"
            and m.state not in ("done", "cancel")
            and not m.move_line_ids.lot_id
        ).product_id
        if missing:
            raise UserError(
                _(
                    "There is no lot available to consume for the components "
                    "below. They may have been returned to stock: separate them "
                    "again before posting to the manufacturing order.\n%s",
                    "\n".join(missing.mapped("display_name")),
                )
            )
