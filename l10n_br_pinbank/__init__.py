from . import models
from . import utils

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'boleto_pinbank')


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'boleto_pinbank')
