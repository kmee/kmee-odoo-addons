# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields, models


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
            )

        if "custom" in self.line_ids.mapped("delay_type"):
            return self._compute_terms_override(
                date_ref,
                currency,
                company,
                tax_amount,
                tax_amount_currency,
                sign,
                untaxed_amount,
                untaxed_amount_currency,
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
        )

    def _compute_terms_override(
        self,
        date_ref,
        currency,
        company,
        tax_amount,
        tax_amount_currency,
        sign,
        untaxed_amount,
        untaxed_amount_currency,
    ):
        """
        Full override of _compute_terms for custom fixed date manual lines.
        """
        self.ensure_one()
        date_ref = date_ref or fields.Date.context_today(self)
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        result = []

        for line in self.line_ids:
            term_vals = {
                "date": date_ref,
                "has_discount": line.discount_percentage,
                "discount_date": False,
                "discount_amount_currency": 0.0,
                "discount_balance": 0.0,
                "discount_percentage": line.discount_percentage,
            }

            if line.value == "fixed":
                term_vals["company_amount"] = sign * currency.round(
                    line.value_amount
                )
                term_vals["foreign_amount"] = sign * currency.round(
                    line.value_amount
                )
            elif line.value == "percent":
                term_vals["company_amount"] = currency.round(
                    total_amount * (line.value_amount / 100.0)
                )
                term_vals["foreign_amount"] = currency.round(
                    total_amount_currency * (line.value_amount / 100.0)
                )
            elif line.value == "balance":
                term_vals["company_amount"] = currency.round(total_amount)
                term_vals["foreign_amount"] = currency.round(total_amount_currency)

            next_date = fields.Date.from_string(date_ref)
            if line.delay_type == "days_after":
                next_date += relativedelta(days=line.nb_days)
            elif line.delay_type == "days_after_end_of_month":
                next_date += relativedelta(day=31)
                next_date += relativedelta(days=line.nb_days)
            elif line.delay_type == "days_after_end_of_next_month":
                next_date += relativedelta(day=31, months=1)
                next_date += relativedelta(days=line.nb_days)
            elif line.delay_type == "custom":
                next_date = line.fixed_date

            term_vals["date"] = next_date
            result.append(term_vals)
            total_amount -= term_vals["company_amount"]
            total_amount_currency -= term_vals["foreign_amount"]

        return result
