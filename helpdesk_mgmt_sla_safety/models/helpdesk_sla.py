from datetime import datetime

from odoo import fields, models


class HelpdeskSla(models.Model):
    _inherit = "helpdesk.sla"

    safety_days = fields.Integer(
        default=0,
        help="Number of days before the deadline for safety alert",
    )
    safety_hours = fields.Integer(
        default=0,
        help="Number of hours before the deadline for safety alert",
    )

    def check_ticket_sla(self, tickets):
        # Chama o método original primeiro
        super().check_ticket_sla(tickets)

        for ticket in tickets:
            working_calendar = ticket.team_id.resource_calendar_id
            create_date = ticket.create_date

            # Calculate safety deadline
            safety_deadline = create_date
            if self.safety_days > 0:
                safety_deadline = working_calendar.plan_days(
                    self.safety_days + 1, safety_deadline, compute_leaves=True
                )
                safety_deadline = safety_deadline.replace(
                    hour=create_date.hour,
                    minute=create_date.minute,
                    second=create_date.second,
                    microsecond=create_date.microsecond,
                )

            safety_deadline = working_calendar.plan_hours(
                self.safety_hours, safety_deadline, compute_leaves=True
            )

            # Update safety deadline and force recompute of safety alert
            ticket.write(
                {
                    "sla_safety_deadline": safety_deadline,
                    "sla_safety_alert": safety_deadline < datetime.now(),
                }
            )
