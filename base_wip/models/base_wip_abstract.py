# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from .base_wip import display_time

# from odoo.osv.orm import setup_modifiers


class BaseWipAbstract(models.AbstractModel):
    _name = "base.wip.abstract"
    _description = "Base Wip Abstract"

    @api.depends("wip_ids")
    def _compute_time(self):
        for record in self:
            lead_time = sum(
                record.wip_ids.filtered(lambda x: not x.state == "done").mapped(
                    "lead_time_seconds"
                )
            )
            cycle_time = sum(
                record.wip_ids.filtered(
                    lambda x: x.state in ("open", "pending")
                ).mapped("lead_time_seconds")
            )
            reaction_time = sum(
                record.wip_ids.filtered(lambda x: x.state == "draft").mapped(
                    "lead_time_seconds"
                )
            )
            logged_time = sum(
                record.wip_ids.filtered(lambda x: x.state == "open").mapped(
                    "lead_time_seconds"
                )
            )

            if lead_time:
                record.flow_efficience = cycle_time / lead_time
            else:
                record.flow_efficience = 0

            record.logged_time_float = logged_time
            record.logged_time = display_time(logged_time, 5)

            record.lead_time_float = lead_time
            record.lead_time = display_time(lead_time, 5)

            record.cycle_time_float = cycle_time
            record.cycle_time = display_time(cycle_time, 5)

            record.reaction_time_float = reaction_time
            record.reaction_time = display_time(reaction_time, 5)

    def _compute_wip_ids(self):
        for record in self:
            record.wip_ids = record.wip_ids.search(
                [("model_id", "=", record._name), ("res_id", "=", record.id)]
            )

    wip_ids = fields.One2many(comodel_name="base.wip", compute="_compute_wip_ids")

    lead_time_float = fields.Float(
        compute="_compute_time",
    )

    lead_time = fields.Char(
        compute="_compute_time",
    )

    cycle_time_float = fields.Float(
        compute="_compute_time",
    )

    cycle_time = fields.Char(
        compute="_compute_time",
    )

    reaction_time_float = fields.Float(
        compute="_compute_time",
    )

    reaction_time = fields.Char(
        compute="_compute_time",
    )

    logged_time_float = fields.Float(
        compute="_compute_time",
    )

    logged_time = fields.Char(
        compute="_compute_time",
    )

    flow_efficience = fields.Float(
        compute="_compute_time",
    )

    # @api.model
    @api.model_create_multi
    def create(self, vals_list):
        result = self.env[self._name]
        for vals in vals_list:
            result |= super().create(vals)
            result.wip_ids.start(
                model_id=self._name,
                res_id=result.id,
                state=vals.get("state", "draft"),
            )
        return result

    def write(self, vals):
        previus_state = self.state
        result = super().write(vals)
        if previus_state != self.state:
            self.wip_ids.stop()
            self.wip_ids.start(model_id=self._name, res_id=self.id, state=self.state)
        return result
