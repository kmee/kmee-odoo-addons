import secrets

from . import controllers
from . import models
from . import utils

from odoo import SUPERUSER_ID, api

from odoo.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(cr, registry):
    setup_provider(cr, registry, "brbank")
    # One webhook token per provider: a column default would give the same
    # token to every record that existed before the install.
    env = api.Environment(cr, SUPERUSER_ID, {})
    for provider in env["payment.provider"].search([("code", "=", "brbank")]):
        provider.brbank_webhook_token = secrets.token_urlsafe(32)


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, "brbank")
