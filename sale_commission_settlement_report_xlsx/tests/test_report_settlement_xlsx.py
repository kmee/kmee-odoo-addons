# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

import xlrd

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportSettlementXlsx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.commission = cls.env["commission"].create(
            {"name": "10%", "fix_qty": 10.0, "invoice_state": "open"}
        )
        cls.agent = cls.env["res.partner"].create(
            {
                "name": "Agent Report",
                "agent": True,
                "settlement": "monthly",
                "commission_id": cls.commission.id,
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Customer Report"})
        cls.product = cls.env["product.product"].create({"name": "Product Report"})
        cls._invoice(100.0, date(2024, 1, 10))
        cls._invoice(200.0, date(2024, 1, 20))
        cls._invoice(300.0, date(2024, 2, 10))
        wizard = cls.env["commission.make.settle"].create(
            {
                "date_to": date(2024, 3, 15),
                "agent_ids": [(4, cls.agent.id)],
                "settlement_type": "sale_invoice",
            }
        )
        action = wizard.action_settle()
        cls.settlements = cls.env["commission.settlement"].search(
            action["domain"], order="date_from"
        )

    @classmethod
    def _invoice(cls, amount, invoice_date):
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.customer.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "quantity": 1,
                            "price_unit": amount,
                            "agent_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "agent_id": cls.agent.id,
                                        "commission_id": cls.commission.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _render(self, settlements):
        report = self.env.ref(
            "sale_commission_settlement_report_xlsx.action_report_settlement_xlsx"
        )
        content, report_type = report._render_xlsx(
            report.report_name, settlements.ids, {}
        )
        self.assertEqual(report_type, "xlsx")
        book = xlrd.open_workbook(file_contents=content)
        sheet = book.sheet_by_index(0)
        return [sheet.row_values(i) for i in range(sheet.nrows)]

    def test_two_settlements_do_not_overlap(self):
        self.assertEqual(len(self.settlements), 2)
        rows = self._render(self.settlements)
        # each settlement: header (4 rows), lines, footer, 2 blank rows
        agents = [r for r in rows if r[0] == "Agent Report"]
        self.assertEqual(len(agents), 2)
        totals = [r[6] for r in rows if r[5] == "Total Commissions"]
        # January: 10% of 100 and 200, February: 10% of 300
        self.assertEqual(totals, [30.0, 30.0])

    def test_total_is_per_settlement(self):
        january = self.settlements[0]
        rows = self._render(january)
        totals = [r[6] for r in rows if r[5] == "Total Commissions"]
        self.assertEqual(totals, [january.total])
        lines = [r for r in rows if r[2] == "Customer Report"]
        self.assertEqual(len(lines), 2)
        self.assertEqual(sorted(r[6] for r in lines), [10.0, 20.0])
        self.assertEqual(rows[0][:3], ["Agent", "From", "To"])
        self.assertEqual(rows[1][1:3], ["2024-01-01", "2024-01-31"])
        for row in lines:
            self.assertEqual(row[2], "Customer Report")
