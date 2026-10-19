# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger

from .common import TierExceptionsMixin


@tagged("post_install", "-at_install")
class TestReportController(TierExceptionsMixin, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tier_exceptions()

    def _download(self, order, report="sale.report_saleorder"):
        return self.url_open("/report/pdf/%s/%d" % (report, order.id))

    def test_report_is_refused_for_order_with_exceptions(self):
        """
        Given a sale order that has exception rules to be validated
        When the user opens the order PDF report route
        Then the report is refused (400, UserError), not delivered
        """
        order = self._order(5000.0)
        self.authenticate("admin", "admin")
        with mute_logger("odoo.http"):
            response = self._download(order)
        self.assertEqual(response.status_code, 400)

    def test_report_is_delivered_for_order_without_exceptions(self):
        """
        Given a sale order that triggers no exception
        When the user opens the order PDF report route
        Then the report is delivered
        """
        order = self._order(10.0)
        self.authenticate("admin", "admin")
        response = self._download(order)
        self.assertEqual(response.status_code, 200)

    def test_report_is_delivered_once_exceptions_are_ignored(self):
        """
        Given an order whose exceptions were approved (ignored)
        When the user opens the order PDF report route
        Then the report is delivered
        """
        order = self._order(5000.0)
        order.write({"ignore_exception": True})
        self.authenticate("admin", "admin")
        self.assertEqual(self._download(order).status_code, 200)

    def test_report_of_other_models_is_not_affected(self):
        """
        Given a report of another model while a sale order has exceptions
        When the report route is opened
        Then the sale exception check does not interfere
        """
        self._order(5000.0).detect_exceptions()
        self.authenticate("admin", "admin")
        module = self.env.ref("base.module_sale")
        response = self.url_open(
            "/report/pdf/base.report_irmodulereference/%d" % module.id
        )
        self.assertEqual(response.status_code, 200)
