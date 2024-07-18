# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def compute(self, value, date_ref=False, currency=None):
        """
        Inherit compute to use manual term id if set.

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
            return manual_payment_term_id.compute(
                value, date_ref=date_ref, currency=currency
            )

        if "custom" in self.line_ids.mapped("option"):
            # No alternative other than complete method override
            # can't call super
            return self.compute_override(value, date_ref=date_ref, currency=currency)

        return super().compute(value, date_ref=date_ref, currency=currency)

    def compute_override(self, value, date_ref=False, currency=None):
        """
        Full override of compute method to fixed date manual lines if set.
        """
        self.ensure_one()
        date_ref = date_ref or fields.Date.context_today(self)
        amount = value
        sign = value < 0 and -1 or 1
        result = []
        if not currency and self.env.context.get("currency_id"):
            currency = self.env["res.currency"].browse(self.env.context["currency_id"])
        elif not currency:
            currency = self.env.company.currency_id
        for line in self.line_ids:
            if line.value == "fixed":
                amt = sign * currency.round(line.value_amount)
            elif line.value == "percent":
                amt = currency.round(value * (line.value_amount / 100.0))
            elif line.value == "balance":
                amt = currency.round(amount)
            next_date = fields.Date.from_string(date_ref)
            if line.option == "day_after_invoice_date":
                next_date += relativedelta(days=line.days)
                if line.day_of_the_month > 0:
                    months_delta = (line.day_of_the_month < next_date.day) and 1 or 0
                    next_date += relativedelta(
                        day=line.day_of_the_month, months=months_delta
                    )
            elif line.option == "after_invoice_month":
                next_first_date = next_date + relativedelta(
                    day=1, months=1
                )  # Getting 1st of next month
                next_date = next_first_date + relativedelta(days=line.days - 1)
            elif line.option == "day_following_month":
                next_date += relativedelta(day=line.days, months=1)
            elif line.option == "day_current_month":
                next_date += relativedelta(day=line.days, months=0)
            elif line.option == "custom":
                next_date = line.fixed_date
            result.append((fields.Date.to_string(next_date), amt))
            amount -= amt
        amount = sum(amt for _, amt in result)
        dist = currency.round(value - amount)
        if dist:
            last_date = result and result[-1][0] or fields.Date.context_today(self)
            result.append((last_date, dist))
        return sorted(result, key=lambda k: k[0])
