# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    quote_summary_enabled = fields.Boolean(
        string="Collapse quoted email history in chatter",
        config_parameter="mail_chatter_quote_summary.enabled",
        default=True,
        help="Show only the most recent reply in chatter messages; the quoted "
        "history is loaded on demand.",
    )
    quote_summary_models = fields.Char(
        string="Restrict to models",
        config_parameter="mail_chatter_quote_summary.models",
        help="Comma-separated technical model names to restrict the feature to "
        "(e.g. helpdesk.ticket,crm.lead). Leave empty to apply to every chatter.",
    )
