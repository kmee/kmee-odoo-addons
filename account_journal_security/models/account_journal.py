# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    allowed_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="account_journal_allowed_group_rel",
        column1="journal_id",
        column2="group_id",
        string="Allowed Groups",
        help="Only the users of these groups see this journal and its entries, "
        "journal items, payments and bank statement lines. "
        "Leave empty to allow every user.",
    )

    @api.model
    def _build_no_journal_error_msg(self, company_name, journal_types):
        domain = [
            *self._check_company_domain(self.env.companies),
            ("type", "in", journal_types),
        ]
        if self.sudo().search_count(domain, limit=1) and not self.search_count(
            domain, limit=1
        ):
            return self.env._(
                "None of your groups is allowed to use a journal of these types "
                "in company %(company_name)s: %(journal_types)s. Ask an "
                "accounting administrator to add one of your groups to the "
                "Allowed Groups of a journal.",
                company_name=company_name,
                journal_types=", ".join(journal_types),
            )
        return super()._build_no_journal_error_msg(company_name, journal_types)
