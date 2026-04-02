# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def _compute_terms(
        self,
        date_ref,
        currency,
        company,
        tax_amount,
        tax_amount_currency,
        sign,
        untaxed_amount,
        untaxed_amount_currency,
        cash_rounding=None,
    ):
        """
        Inherit _compute_terms to use manual term id if set.

        manual_payment_term_id must be set
        manual_payment_term_id must have manual lines (else just use normal term_id)
        if self == manual_payment_term_id there's no need to override this method

        complete override for terms with fixed dates > look for alternatives
        """
        manual_payment_term_id = self.env.context.get("manual_payment_term_id")
        if (
            manual_payment_term_id
            and manual_payment_term_id.has_manual_lines
            and self is not manual_payment_term_id
        ):
            return manual_payment_term_id._compute_terms(
                date_ref,
                currency,
                company,
                tax_amount,
                tax_amount_currency,
                sign,
                untaxed_amount,
                untaxed_amount_currency,
                cash_rounding=cash_rounding,
            )

        has_custom_lines = any(
            line.fixed_date for line in self.line_ids if hasattr(line, "fixed_date")
        )
        if has_custom_lines:
            return self._compute_terms_with_fixed_dates(
                date_ref,
                currency,
                company,
                tax_amount,
                tax_amount_currency,
                sign,
                untaxed_amount,
                untaxed_amount_currency,
                cash_rounding=cash_rounding,
            )

        return super()._compute_terms(
            date_ref,
            currency,
            company,
            tax_amount,
            tax_amount_currency,
            sign,
            untaxed_amount,
            untaxed_amount_currency,
            cash_rounding=cash_rounding,
        )

    def _compute_terms_with_fixed_dates(
        self,
        date_ref,
        currency,
        company,
        tax_amount,
        tax_amount_currency,
        sign,
        untaxed_amount,
        untaxed_amount_currency,
        cash_rounding=None,
    ):
        """
        Override of _compute_terms that supports fixed date lines.

        Uses the standard computation but replaces the due date for lines
        that have a fixed_date set.
        """
        self.ensure_one()
        company_currency = company.currency_id
        tax_amount_left = tax_amount
        tax_amount_currency_left = tax_amount_currency
        untaxed_amount_left = untaxed_amount
        untaxed_amount_currency_left = untaxed_amount_currency
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        result = []

        for line in self.line_ids.sorted(lambda l: l.value == "balance"):
            # Use fixed_date if available, otherwise standard due date
            if hasattr(line, "fixed_date") and line.fixed_date:
                due_date = line.fixed_date
            else:
                due_date = line._get_due_date(date_ref)

            term_vals = {
                "date": due_date,
                "has_discount": line.discount_percentage,
                "discount_date": None,
                "discount_amount_currency": 0.0,
                "discount_balance": 0.0,
                "discount_percentage": line.discount_percentage,
            }

            if line.value == "fixed":
                term_vals["company_amount"] = sign * company_currency.round(
                    line.value_amount
                )
                term_vals["foreign_amount"] = sign * currency.round(line.value_amount)
                company_proportion = (
                    tax_amount / untaxed_amount if untaxed_amount else 1
                )
                foreign_proportion = (
                    tax_amount_currency / untaxed_amount_currency
                    if untaxed_amount_currency
                    else 1
                )
                line_tax_amount = (
                    company_currency.round(line.value_amount * company_proportion)
                    * sign
                )
                line_tax_amount_currency = (
                    currency.round(line.value_amount * foreign_proportion) * sign
                )
                line_untaxed_amount = term_vals["company_amount"] - line_tax_amount
                line_untaxed_amount_currency = (
                    term_vals["foreign_amount"] - line_tax_amount_currency
                )
            elif line.value == "percent":
                term_vals["company_amount"] = company_currency.round(
                    total_amount * (line.value_amount / 100.0)
                )
                term_vals["foreign_amount"] = currency.round(
                    total_amount_currency * (line.value_amount / 100.0)
                )
                line_tax_amount = company_currency.round(
                    tax_amount * (line.value_amount / 100.0)
                )
                line_tax_amount_currency = currency.round(
                    tax_amount_currency * (line.value_amount / 100.0)
                )
                line_untaxed_amount = term_vals["company_amount"] - line_tax_amount
                line_untaxed_amount_currency = (
                    term_vals["foreign_amount"] - line_tax_amount_currency
                )
            else:
                line_tax_amount = 0.0
                line_tax_amount_currency = 0.0
                line_untaxed_amount = 0.0
                line_untaxed_amount_currency = 0.0

            tax_amount_left -= line_tax_amount
            tax_amount_currency_left -= line_tax_amount_currency
            untaxed_amount_left -= line_untaxed_amount
            untaxed_amount_currency_left -= line_untaxed_amount_currency

            if line.value == "balance":
                term_vals["foreign_amount"] = (
                    tax_amount_currency_left + untaxed_amount_currency_left
                )
                term_vals["company_amount"] = tax_amount_left + untaxed_amount_left

            if line.discount_percentage:
                if company.early_pay_discount_computation in ("excluded", "mixed"):
                    term_vals["discount_balance"] = company_currency.round(
                        term_vals["company_amount"]
                        - line_untaxed_amount * line.discount_percentage / 100.0
                    )
                    term_vals["discount_amount_currency"] = currency.round(
                        term_vals["foreign_amount"]
                        - line_untaxed_amount_currency
                        * line.discount_percentage
                        / 100.0
                    )
                else:
                    term_vals["discount_balance"] = company_currency.round(
                        term_vals["company_amount"]
                        * (1 - (line.discount_percentage / 100.0))
                    )
                    term_vals["discount_amount_currency"] = currency.round(
                        term_vals["foreign_amount"]
                        * (1 - (line.discount_percentage / 100.0))
                    )
                term_vals["discount_date"] = date_ref + relativedelta(
                    days=line.discount_days
                )

            result.append(term_vals)
        return result
