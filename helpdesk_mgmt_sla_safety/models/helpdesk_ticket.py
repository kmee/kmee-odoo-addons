from datetime import datetime

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    sla_safety_deadline = fields.Datetime(
        string="SLA Safety Deadline",
        help="Safety deadline before the final SLA deadline",
    )
    sla_safety_alert = fields.Boolean(
        string="SLA Safety Alert",
        compute="_compute_sla_safety_alert",
        store=True,
        help="True when current time has passed the safety deadline",
    )

    @api.depends("sla_safety_deadline")
    def _compute_sla_safety_alert(self):
        now = datetime.now()
        for ticket in self:
            if ticket.sla_safety_deadline:
                ticket.sla_safety_alert = ticket.sla_safety_deadline < now
            else:
                ticket.sla_safety_alert = False
