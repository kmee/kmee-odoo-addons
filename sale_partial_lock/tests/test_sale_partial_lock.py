# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSalePartialLock(TransactionCase):
    def test_form_view_buttons_for_locked_orders(self):
        arch = self.env["sale.order"].get_view(
            self.env.ref("sale.view_order_form").id, "form"
        )["arch"]
        if isinstance(arch, bytes):
            arch = arch.decode()
        self.assertIn("state != 'done'", arch)
        self.assertIn("invoice_status != 'to invoice' and state != 'done'", arch)
