# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from .models.mail_message import ENABLED_PARAM


def post_init_hook(env):
    """Enable the feature by default on a fresh install only."""
    params = env["ir.config_parameter"]
    if params.get_str(ENABLED_PARAM, None) is None:
        params.set_bool(ENABLED_PARAM, True)
