# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class GroupedPurchaseRequisition(models.TransientModel):
    _name = "grouped.purchase.requisition"
    _description = "Purchase Agreement Totals by Product"

    requisition_id = fields.Many2one("purchase.requisition", required=True)
    grouped_line_ids = fields.One2many(
        "grouped.requisition.line", "wizard_id", string="Totals"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        requisition = self.env["purchase.requisition"].browse(res.get("requisition_id"))
        if requisition:
            res["grouped_line_ids"] = [
                (0, 0, vals) for vals in self._prepare_grouped_lines(requisition)
            ]
        return res

    @api.model
    def _prepare_grouped_lines(self, requisition):
        grouped = {}
        for line in requisition.line_ids.filtered("product_id"):
            data = grouped.setdefault(
                (line.product_id, line.product_uom_id),
                {"product_qty": 0.0, "dates": []},
            )
            data["product_qty"] += line.product_qty
            if line.schedule_date:
                data["dates"].append(line.schedule_date)
        po_lines = requisition.purchase_ids.filtered(
            lambda o: o.state in ("purchase", "done")
        ).order_line
        result = []
        for (product, uom), data in grouped.items():
            ordered = sum(
                po_line.product_uom._compute_quantity(po_line.product_qty, uom)
                for po_line in po_lines.filtered(
                    lambda ol, p=product: ol.product_id == p
                )
            )
            result.append(
                {
                    "product_id": product.id,
                    "product_uom_id": uom.id,
                    "product_qty": data["product_qty"],
                    "qty_ordered": ordered,
                    "schedule_date": min(data["dates"]) if data["dates"] else False,
                }
            )
        return result


class GroupedRequisitionLine(models.TransientModel):
    _name = "grouped.requisition.line"
    _description = "Purchase Agreement Totals by Product Line"

    wizard_id = fields.Many2one("grouped.purchase.requisition", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product")
    product_uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    product_qty = fields.Float(string="Needed", digits="Product Unit of Measure")
    qty_ordered = fields.Float(string="Ordered", digits="Product Unit of Measure")
    schedule_date = fields.Date(string="Earliest Scheduled Date")
