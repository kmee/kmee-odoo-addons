# Copyright 2025 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.tools.translate import _

from odoo.addons.report_py3o.controllers import main as report


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report_action = request.env["ir.actions.report"]._get_report_from_name(
            reportname
        )
        if report_action.model == "sale.order":
            ids = []
            if docids:
                ids = [int(i) for i in docids.split(",")]
            for sale_order_id in ids:
                sale_order = request.env["sale.order"].browse(sale_order_id)
                if sale_order.detect_exceptions():
                    raise UserError(
                        _(
                            "The report cannot be generated because the "
                            "quote has exceptions that need to be validated."
                        )
                    )

        return super().report_routes(
            reportname=reportname, docids=docids, converter=converter, **data
        )
