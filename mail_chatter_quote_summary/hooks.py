# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from .models.mail_message import ENABLED_PARAM


def post_init_hook(cr, registry):
    """Enable the feature by default on a fresh install only."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"]
    if params.get_param(ENABLED_PARAM) is False:
        params.set_param(ENABLED_PARAM, "True")
