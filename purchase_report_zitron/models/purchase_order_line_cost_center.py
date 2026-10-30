# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _zitron_report_cost_center(self):
        """Cost center text of the line for the PDF.

        Built from ``analytic_distribution`` (keys are comma separated
        analytic account ids, values are percentages): "7001 Name" for a
        single account at 100%, "7001 Name 60% / 7002 Other 40%" when split.
        """
        self.ensure_one()
        distribution = self.analytic_distribution or {}
        parts = []
        for key, percentage in distribution.items():
            accounts = self.env["account.analytic.account"].browse(
                [int(x) for x in str(key).split(",") if x]
            )
            name = ", ".join(
                " ".join(filter(None, [acc.code, acc.name])) for acc in accounts
            )
            if not name:
                continue
            if len(distribution) > 1 or abs(percentage - 100) > 0.005:
                name = "%s %s%%" % (name, ("%.2f" % percentage).rstrip("0").rstrip("."))
            parts.append(name)
        return " / ".join(parts)
