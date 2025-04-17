from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("at_install", "post_install")
class TestL10nBrPaymentBoleto(TransactionCase):
    def setUp(self):
        super().setUp()

        # Create a demo payment.provider
        self.payment_provider = self.env["payment.provider"].create(
            {
                "name": "Test Payment Provider",
                "code": "none",
                "state": "enabled",
            }
        )

        # Create a demo payment.mode
        self.payment_mode = self.env["account.payment.mode"].create(
            {
                "name": "Test Payment Mode",
                "bank_account_link": "fixed",
                "fixed_journal_id": self.env["account.journal"]
                .search([("code", "=", "CSH1")])
                .id,
                "generate_boletos_on_invoice": True,
                "payment_provider_id": self.payment_provider.id,
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
            }
        )

        # Create a demo account.move
        self.account_move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.env.ref("base.res_partner_1").id,
                "invoice_date": "2023-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Product",
                            "quantity": 1,
                            "price_unit": 100.0,
                        },
                    )
                ],
                "payment_mode_id": self.payment_mode.id,
            }
        )

    def test_generate_boletos_on_invoice_enable(self):
        """
        Test the generation of boletos when the feature is enabled on an invoice.

        This test verifies that the `generate_boletos` method is called exactly once
        when an account move (invoice) is confirmed (posted). The method is patched
        to ensure that no actual boleto generation logic is executed during the test.

        Steps:
        1. Patch the `generate_boletos` method of the `AccountMove` model.
        2. Confirm (post) the account move.
        3. Assert that the `generate_boletos` method was called exactly once.

        Expected Result:
        - The `generate_boletos` method is invoked once upon posting the account move.
        """
        with patch(
            "odoo.addons.l10n_br_payment_boleto.models.account_move."
            "AccountMove.generate_boletos"
        ) as mock_generate_boletos:
            # Confirm the account.move
            self.account_move.action_post()

            # Assert that generate_boletos was called exactly once
            mock_generate_boletos.assert_called_once()

    def test_generate_boletos_on_invoice_disable(self):
        """
        Test case for verifying that boletos are not generated when the
        'generate_boletos_on_invoice' flag is disabled.

        This test ensures that the `generate_boletos` method is not called
        when the `generate_boletos_on_invoice` attribute of the payment mode
        is set to `False`.

        Steps:
        1. Set `generate_boletos_on_invoice` to `False`.
        2. Mock the `generate_boletos` method of the `AccountMove` model.
        3. Post the account move using the `action_post` method.
        4. Assert that the `generate_boletos` method was not called.

        Expected Behavior:
        - The `generate_boletos` method should not be invoked when
          `generate_boletos_on_invoice` is disabled.
        """
        self.payment_mode.generate_boletos_on_invoice = False

        with patch(
            "odoo.addons.l10n_br_payment_boleto.models.account_move."
            "AccountMove.generate_boletos"
        ) as mock_generate_boletos:
            # Confirm the account.move
            self.account_move.action_post()

            # Assert that generate_boletos was not called
            mock_generate_boletos.assert_not_called()
