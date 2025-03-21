# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models, tools

from .base_wip import display_time

# from odoo.osv.orm import setup_modifiers


class BaseWipReport(models.Model):
    _name = "base.wip.report"
    _description = "Base WIP Report"
    _auto = False

    model_id = fields.Many2one(comodel_name="ir.model")
    res_id = fields.Integer(
        string="Resource ID",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "New"),
            ("open", "In Progress"),
            ("pending", "Pending"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
            ("exception", "Exception"),
        ],
        # string="Wip State",
        index=True,
    )

    reference_id = fields.Reference(
        string="Record",
        selection=[("project.task", "Project Task")],
        compute="_compute_time",
    )

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

    @api.depends("model_id", "res_id")
    def _compute_time(self):
        for record in self:
            record.reference_id = "%s,%s" % (record.model_id.model, record.res_id)
            wip_ids = record.env["base.wip"].search(
                [("model_id", "=", record.model_id.id), ("res_id", "=", record.res_id)]
            )
            lead_time = sum(
                wip_ids.filtered(lambda x: not x.state == "done").mapped(
                    "lead_time_seconds"
                )
            )
            cycle_time = sum(
                wip_ids.filtered(lambda x: x.state in ("open", "pending")).mapped(
                    "lead_time_seconds"
                )
            )
            reaction_time = sum(
                wip_ids.filtered(lambda x: x.state == "draft").mapped(
                    "lead_time_seconds"
                )
            )
            logged_time = sum(
                wip_ids.filtered(lambda x: x.state == "open").mapped(
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

    # @api.multi
    def open_form(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.reference_id.name,
            "view_type": "form",
            "view_mode": "form",
            "res_model": self.model_id.model,
            "res_id": self.res_id,
            "target": "current",
        }

    # @api.model_cr
    def init(self):
        """
        CRM Lead Report
        @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(self._cr, "base_wip_report")
        self._cr.execute(
            """
                CREATE OR REPLACE VIEW base_wip_report AS (
                with initial as (select
                    max(id) as id, res_id, model_id
                from base_wip
                group by res_id, model_id)
                select
                    id, res_id, model_id, state
                from base_wip
                where id in (select id from initial)
                group by id, res_id, model_id, state
                )"""
        )
