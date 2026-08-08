# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import FISCAL_IN

from ..constants import FISCAL_FIELD, FISCAL_FIELD_ITEM_LEVEL

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        self._generate_double_entry_lines()
        return posted

    def button_draft(self):
        self._remove_double_entry_lines()
        return super().button_draft()

    def _generate_double_entry_lines(self):
        """Generate double-entry lines from fiscal template for each move."""
        for move in self:
            template = move.fiscal_operation_id.account_move_template_id
            if not template:
                continue

            # Remove previously generated lines for idempotency
            move._remove_double_entry_lines()

            all_items = template._get_all_items()
            if not all_items:
                continue

            line_vals_list = []
            for inv_line in move.invoice_line_ids.filtered(
                lambda line: line.fiscal_operation_line_id
            ):
                fields_done = set()
                for item in all_items:
                    vals = move._prepare_double_entry_vals(inv_line, item, fields_done)
                    line_vals_list.extend(vals)

            if line_vals_list:
                self.env["account.move.line"].with_context(
                    check_move_validity=False,
                    skip_invoice_sync=True,
                ).create(line_vals_list)

    def _prepare_double_entry_vals(self, inv_line, template_item, fields_done):
        """Prepare debit/credit line vals for a single template item.

        Returns a list of 0 or 2 dicts (debit + credit pair).
        """
        fiscal_field = template_item.fiscal_field
        if fiscal_field in fields_done:
            return []

        value = getattr(inv_line, fiscal_field, 0.0)
        if not value:
            return []

        # Tax credit check for purchase operations
        if template_item.require_tax_credit and self.fiscal_operation_type == FISCAL_IN:
            tax_domain = template_item.tax_domain
            if tax_domain and not self._has_tax_credit(inv_line, tax_domain):
                return []

        account_debit = self._resolve_account(inv_line, template_item, "debit")
        account_credit = self._resolve_account(inv_line, template_item, "credit")

        if not account_debit or not account_credit:
            _logger.warning(
                "Template item '%s' field '%s': could not resolve "
                "debit/credit accounts for line '%s' on move '%s'. "
                "Debit=%s, Credit=%s",
                template_item.template_id.name,
                fiscal_field,
                inv_line.name,
                self.name,
                account_debit,
                account_credit,
            )
            return []

        fields_done.add(fiscal_field)

        label = dict(FISCAL_FIELD).get(fiscal_field, fiscal_field)
        name = "[{}] {}".format(label, inv_line.name or "")

        due_date = (
            self.invoice_date_due
            or self.invoice_date
            or self.date
            or fields.Date.context_today(self)
        )

        receivable_payable = ("asset_receivable", "liability_payable")

        common_vals = {
            "move_id": self.id,
            "name": name,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "is_double_entry_line": True,
        }

        # Os campos fiscais sao expressos na moeda da empresa (BRL). Numa
        # fatura em moeda estrangeira, o amount_currency precisa ser convertido
        # para a moeda do documento, senao as linhas geradas ficam com par
        # balance/amount_currency inconsistente.
        company_currency = self.company_id.currency_id
        amount_currency = value
        if self.currency_id and self.currency_id != company_currency:
            amount_currency = company_currency._convert(
                value,
                self.currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )

        debit_vals = dict(
            common_vals,
            account_id=account_debit.id,
            balance=value,
            amount_currency=amount_currency,
        )
        credit_vals = dict(
            common_vals,
            account_id=account_credit.id,
            balance=-value,
            amount_currency=-amount_currency,
        )

        # Set display_type based on account type to satisfy Odoo constraints:
        # receivable/payable accounts require display_type='payment_term'
        for vals, account in [
            (debit_vals, account_debit),
            (credit_vals, account_credit),
        ]:
            if account.account_type in receivable_payable:
                vals["display_type"] = "payment_term"
                vals["date_maturity"] = due_date
            else:
                vals["display_type"] = "cogs"
        return [debit_vals, credit_vals]

    def _has_tax_credit(self, line, tax_domain):
        """Check if the fiscal line has tax credit rights for the given domain."""
        if tax_domain in ("icms", "icmssn"):
            return line.icms_cst_code in ("00", "20", "60", "70")
        elif tax_domain == "icmsst":
            # ST credit depends on specific CST
            return line.icms_cst_code in ("60",)
        elif tax_domain == "ipi":
            return line.ipi_cst_code in ("00", "01", "02", "03", "04", "05")
        elif tax_domain == "pis":
            return bool(line.pis_credit_id)
        elif tax_domain == "cofins":
            return bool(line.cofins_credit_id)
        return True

    def _resolve_account(self, inv_line, template_item, side):
        """Resolve account for debit or credit side using fallback cascade.

        Cascade:
        1. Template item explicit account
        2. Product category account (for item-level fields)
        3. Partner account (for document-level fields)
        4. Journal default account
        """
        # 1. Explicit template account
        if side == "debit" and template_item.account_debit_id:
            return template_item.account_debit_id
        if side == "credit" and template_item.account_credit_id:
            return template_item.account_credit_id

        is_out = self.fiscal_operation_type != FISCAL_IN
        product = inv_line.product_id

        # 2. Product category accounts (for item-level fields)
        if template_item.fiscal_field in FISCAL_FIELD_ITEM_LEVEL and product:
            if is_out:
                account = (
                    product.property_account_income_id
                    or product.categ_id.property_account_income_categ_id
                )
            else:
                account = (
                    product.property_account_expense_id
                    or product.categ_id.property_account_expense_categ_id
                )
            if account:
                return account

        # 3. Partner accounts (for document-level fields)
        partner = self.partner_id
        if partner:
            if is_out:
                account = partner.property_account_receivable_id
            else:
                account = partner.property_account_payable_id
            if account:
                return account

        # 4. Journal default account
        journal = self.journal_id
        if journal and journal.default_account_id:
            return journal.default_account_id

        return None

    def _remove_double_entry_lines(self):
        """Remove previously generated template lines."""
        for move in self:
            template_lines = move.line_ids.filtered(
                lambda line: line.is_double_entry_line
            )
            if template_lines:
                template_lines.with_context(
                    check_move_validity=False,
                    skip_invoice_sync=True,
                    dynamic_unlink=True,
                    force_delete=True,
                ).unlink()
