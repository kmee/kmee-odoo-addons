# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Rename "OC" to "Pedido" in the stored PDF note (HD1801).

    Only the exact old wording is replaced, so customized notes are untouched.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([]):
        note = company.purchase_report_footer_note
        if note and "número desta OC," in note:
            company.purchase_report_footer_note = note.replace(
                "número desta OC,", "número deste Pedido,"
            )
