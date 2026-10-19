# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInstallments(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Term = cls.env["account.payment.term"]
        cls.provider = cls.env["payment.provider"].create(
            {"name": "Installment Provider", "code": "none"}
        )
        cls.other_provider = cls.env["payment.provider"].create(
            {"name": "Other Provider", "code": "none"}
        )

    def _term(self, n, rate=0.0, kind="simple", provider=None, installment=True):
        """Create a term with ``n`` installment lines (n-1 percent + balance)."""
        lines = []
        for i in range(n - 1):
            lines.append(
                (
                    0,
                    0,
                    {
                        "value": "percent",
                        "value_amount": round(100.0 / n, 2),
                        "days": 30 * (i + 1),
                    },
                )
            )
        lines.append((0, 0, {"value": "balance", "days": 30 * n}))
        return self.Term.create(
            {
                "name": "%sx %s %s" % (n, kind, rate),
                "is_installment": installment,
                "installment_rate": rate,
                "installment_type": kind,
                "provider_id": provider.id if provider else False,
                "line_ids": lines,
            }
        )

    # compute_installment_options
    def test_term_defaults(self):
        """Given a new term, Then it does not allow installments and uses simple interest."""
        term = self.Term.create({"name": "Plain"})
        self.assertFalse(term.is_installment)
        self.assertEqual(term.installment_type, "simple")
        self.assertEqual(term.installment_rate, 0.0)

    def test_not_installment_term_returns_single_payment(self):
        """Given a term not flagged as installment, When computing options,
        Then only the 1x label is returned even with several lines."""
        term = self._term(3, rate=5.0, installment=False)
        self.assertEqual(term.compute_installment_options(300), ["1x de R$ 300.00"])

    def test_single_line_term_returns_single_payment(self):
        """Given an installment term with a single line, Then it yields 1x."""
        term = self._term(1, rate=5.0)
        self.assertEqual(term.compute_installment_options(150), ["1x de R$ 150.00"])

    def test_simple_interest_without_rate(self):
        """Given 3 installments at 0%, Then each is a third, labeled interest free."""
        term = self._term(3)
        self.assertEqual(
            term.compute_installment_options(300), ["3x de R$ 100.00 sem juros"]
        )

    def test_simple_interest_with_rate(self):
        """Given 3 installments at 2% simple, When amount is 300,
        Then total = 300 * (1 + 0.02 * 2) = 312 and each is 104.00."""
        term = self._term(3, rate=2.0, kind="simple")
        self.assertEqual(
            term.compute_installment_options(300), ["3x de R$ 104.00 com juros"]
        )

    def test_compound_interest_with_rate(self):
        """Given 12 installments at 1% compound on 1000,
        Then the annuity payment is 88.85 (known PMT value)."""
        term = self._term(12, rate=1.0, kind="compose")
        self.assertEqual(
            term.compute_installment_options(1000), ["12x de R$ 88.85 com juros"]
        )

    def test_compound_interest_costs_more_than_interest_free(self):
        """Given the same plan with and without rate, Then rated installment
        is higher than the interest free one."""
        free = self._term(6, rate=0.0, kind="simple")
        rated = self._term(6, rate=3.0, kind="compose")
        per_free = float(free.compute_installment_options(600)[0].split("R$ ")[1][:6])
        per_rated = float(rated.compute_installment_options(600)[0].split("R$ ")[1][:6])
        self.assertEqual(per_free, 100.0)
        self.assertGreater(per_rated, per_free)

    def test_compound_interest_zero_rate(self):
        """Given 3 installments at 0% compound, When computing options,
        Then it does not divide by zero and each is a third."""
        term = self._term(3, rate=0.0, kind="compose")
        self.assertEqual(
            term.compute_installment_options(300), ["3x de R$ 100.00 sem juros"]
        )

    # provider
    def test_provider_options_default_first(self):
        """Given a provider without installment terms, Then only 1x is offered."""
        options = self.provider.get_installment_options(200)
        self.assertEqual(
            options, [{"label": "1x de R$ 200.00 sem juros", "value": "1"}]
        )

    def test_provider_options_sorted_and_filtered(self):
        """Given terms of 6x, 2x (this provider), 4x (other provider) and a 3x
        not flagged as installment, Then the options are 1x, 2x, 6x in that order."""
        self._term(6, rate=1.0, kind="compose", provider=self.provider)
        self._term(2, rate=0.0, provider=self.provider)
        self._term(4, rate=0.0, provider=self.other_provider)
        self._term(3, rate=0.0, provider=self.provider, installment=False)
        options = self.provider.get_installment_options(600)
        self.assertEqual([o["value"] for o in options], ["1", "2", "6"])
        self.assertEqual(options[1]["label"], "2x de R$ 300.00 sem juros")
        self.assertIn("6x de R$", options[2]["label"])
        self.assertIn("com juros", options[2]["label"])

    def test_provider_options_requires_single_record(self):
        """Given two providers, When asking options, Then ensure_one fails."""
        with self.assertRaises(ValueError):
            (self.provider | self.other_provider).get_installment_options(10)

    # transaction
    def _tx(self, provider):
        return self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "reference": "TX-INST-%s" % provider.id,
                "amount": 300.0,
                "currency_id": self.env.company.currency_id.id,
                "partner_id": self.env["res.partner"]
                .create({"name": "Installment Buyer"})
                .id,
            }
        )

    def test_transaction_default_installment_number(self):
        """Given a new transaction, Then it defaults to a single installment."""
        tx = self._tx(self.provider)
        self.assertEqual(tx.installment_number, 1)

    def test_transaction_options_use_term_id_as_value(self):
        """Given an installment term of this provider, When the transaction asks
        for options, Then the value is the term id and the amount is the tx amount."""
        term = self._term(3, rate=2.0, kind="simple", provider=self.provider)
        self._term(2, provider=self.other_provider)
        tx = self._tx(self.provider)
        self.assertEqual(
            tx.get_installment_options(),
            [{"label": "3x de R$ 104.00 com juros", "value": term.id}],
        )

    def test_transaction_without_terms_has_no_options(self):
        """Given a provider without installment terms, Then no option is listed."""
        self.assertEqual(self._tx(self.other_provider).get_installment_options(), [])

    def test_provider_unlink_clears_term_provider(self):
        """Given a term bound to a provider, When the provider is deleted,
        Then the term remains with the provider cleared (ondelete set null)."""
        provider = self.env["payment.provider"].create(
            {"name": "Temp Provider", "code": "none"}
        )
        term = self._term(2, provider=provider)
        provider.unlink()
        self.assertTrue(term.exists())
        self.assertFalse(term.provider_id)

    def test_parent_term_ondelete_set_null(self):
        """Given a term with a parent term, When the parent is deleted,
        Then the child keeps existing without parent."""
        parent = self._term(2)
        child = self._term(3)
        child.payment_term_id = parent
        parent.unlink()
        self.assertFalse(child.payment_term_id)
