# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class HelpdeskTicketSla(models.Model):
    _inherit = "helpdesk.ticket.sla"

    @api.depends("sla_id.use_formula", "sla_id.sla_deadline_formula")
    def _compute_deadline(self):
        standard = self.browse()
        for record in self:
            sla = record.sla_id
            deadline = False
            if sla.use_formula and sla.sla_deadline_formula:
                deadline = sla._eval_deadline_formula(record.ticket_id)
            if deadline:
                record.deadline = deadline
            else:
                standard |= record
        super(HelpdeskTicketSla, standard)._compute_deadline()
