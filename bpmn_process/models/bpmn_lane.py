# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class BpmnLane(models.Model):
    _name = "bpmn.lane"
    _description = "BPMN Lane"
    _order = "process_id, sequence, id"

    process_id = fields.Many2one(
        "bpmn.process", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="process_id.company_id", store=True)
    bpmn_id = fields.Char(string="BPMN Id", required=True, readonly=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    group_ids = fields.Many2many(
        "res.groups",
        string="Groups",
        help="Users of these groups see the tasks of this lane highlighted in "
        "the 'My tasks' layer of the diagram (training map by role).",
    )
    element_ids = fields.One2many("bpmn.element", "lane_id", string="Elements")

    _sql_constraints = [
        (
            "bpmn_id_process_uniq",
            "unique(process_id, bpmn_id)",
            "A lane id must be unique within the process.",
        )
    ]

    def _is_mine(self):
        self.ensure_one()
        return bool(self.group_ids & self.env.user.groups_id)
