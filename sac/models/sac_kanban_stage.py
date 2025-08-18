# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SacKanbanStage(models.Model):
    _order = "sequence"
    _name = "sac.kanban.stage"

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        # domain="[('res_model_id', '=', 'model_id')]",
        help="If set an email will be sent to the customer "
        "when the sac reaches this step.",
    )

    name = fields.Char(
        string="Stage Name",
        translate=True,
        required=True,
        help="Displayed as the header for this stage in Kanban views",
    )
    description = fields.Text(
        translate=True,
        help="Short description of the stage's meaning/purpose",
    )
    sequence = fields.Integer(
        default=1,
        required=True,
        index=True,
        help="Order of stage in relation to other stages available for the"
        " same model",
    )
    legend_priority = fields.Text(
        string="Priority Explanation",
        translate=True,
        default="Mark a card as medium or high priority (one or two stars) to"
        " indicate that it should be escalated ahead of others with"
        " lower priority/star counts.",
        help="Explanation text to help users understand how the priority/star"
        " mechanism applies to this stage",
    )
    legend_blocked = fields.Text(
        string="Special Handling Explanation",
        translate=True,
        default="Give a card the special handling status to indicate that it"
        " requires handling by a special user or subset of users.",
        help="Explanation text to help users understand how the special"
        " handling status applies to this stage",
    )
    legend_done = fields.Text(
        string="Ready Explanation",
        translate=True,
        default="Mark a card as ready when it has been fully processed.",
        help="Explanation text to help users understand how the ready status"
        " applies to this stage",
    )
    legend_normal = fields.Text(
        string="Normal Handling Explanation",
        translate=True,
        default="This is the default status and indicates that a card can be"
        " processed by any user working this queue.",
        help="Explanation text to help users understand how the normal"
        " handling status applies to this stage",
    )
    fold = fields.Boolean(
        string="Collapse?",
        help="Determines whether this stage will be collapsed down in Kanban" " views",
    )
