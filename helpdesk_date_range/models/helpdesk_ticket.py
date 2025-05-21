from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    date_range_id = fields.Many2one(
        comodel_name="date.range",
        string="Reference Period",
        domain="[('type_id.active', '=', True)]",
        help="Period to which the ticket refers, such as month or quarter of competence.",
    )
