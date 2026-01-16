# Copyright (C) 2025-Today - KMEE (<https://kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    programmed_picking_ids = fields.Many2many(
        relation="stock_landed_cost_programmed_picking_rel",
        column1="landed_cost_id",
        column2="picking_id",
        comodel_name="stock.picking",
        string="Programmed Pickings",
        copy=False,
        states={"done": [("readonly", True)]},
        help="Pickings that are scheduled (not applied) to this landed cost. "
        "They can be pickings not yet done; once all are done you can 'Apply Programmed"
        " Pickings'.",
    )

    programmed_state = fields.Selection(
        selection=[
            ("", ""),
            ("programmed", "Programmed"),
            ("ready", "Ready"),
            ("applied", "Applied"),
        ],
        default="",
        compute="_compute_programmed_state",
        store=True,
        readonly=True,
    )

    @api.depends("programmed_picking_ids", "programmed_picking_ids.state")
    def _compute_programmed_state(self):
        for rec in self:
            programmed_ids = rec.programmed_picking_ids
            if not programmed_ids:
                rec.programmed_state = ""
                continue

            if rec.picking_ids and rec.picking_ids == rec.programmed_picking_ids:
                rec.programmed_state = "applied"
                continue

            pending = programmed_ids.filtered(lambda p: p.state != "done")
            if pending:
                rec.programmed_state = "programmed"
            else:
                rec.programmed_state = "ready"

    def action_apply_programmed_pickings(self, clear_programmed=False):
        self.ensure_one()
        programmed_ids = self.programmed_picking_ids
        if not programmed_ids:
            raise UserError(self.env._("There are no programmed pickings to apply."))

        pending = programmed_ids.filtered(lambda p: p.state != "done")
        if pending:
            names = ", ".join(pending.mapped("name") or [str(p.id) for p in pending])
            raise UserError(
                self.env._(
                    "Cannot apply programmed pickings because the following pickings "
                    "are not done: %s"
                )
                % names
            )

        add_commands = [(4, p.id) for p in programmed_ids]
        self.write({"picking_ids": add_commands})
        self.programmed_state = "applied"

        if clear_programmed:
            self.programmed_picking_ids = [(5, 0, 0)]

        return True

    def button_apply_programmed_pickings(self):
        for rec in self:
            rec.action_apply_programmed_pickings()
        return True

    def button_validate(self):
        if self.filtered(lambda lc: lc.programmed_state not in ["applied", "", False]):
            raise UserError(
                self.env._(
                    "You cannot validate a landed cost with programmed pickings not yet"
                    " applied."
                )
            )
        res = super().button_validate()
        return res
