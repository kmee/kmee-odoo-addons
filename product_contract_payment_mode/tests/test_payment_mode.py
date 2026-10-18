from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductContractPaymentMode(TransactionCase):
    def test_contract_values_carry_payment_mode(self):
        payment_mode = self.env["account.payment.mode"].search([], limit=1)
        if not payment_mode:
            payment_mode = self.env["account.payment.mode"].create(
                {
                    "name": "Test mode",
                    "bank_account_link": "variable",
                    "payment_method_id": self.env.ref(
                        "account.account_payment_method_manual_in"
                    ).id,
                }
            )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Customer"}).id,
                "payment_mode_id": payment_mode.id,
            }
        )
        values = order._prepare_contract_value(self.env["contract.template"])
        self.assertEqual(values["payment_mode_id"], payment_mode.id)
