# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# Author: Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    is_custom = fields.Boolean(
        string="Custom Term",
        default=False,
        help="Indicates if this payment term is record-specific and editable.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        terms = super().create(vals_list)
        terms.filtered("is_custom").active = False
        return terms

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_custom"):
            self.filtered("is_custom").active = False
        return res

    def copy_term_id_as_custom(self, name="Custom"):
        """
        Creates a copy of the current record with the specified name.

        :param name: The name for the new record.
        :return: The newly created record.
        """
        self.ensure_one()
        custom_term_id = self.copy({"name": name, "is_custom": True, "active": False})
        return custom_term_id
