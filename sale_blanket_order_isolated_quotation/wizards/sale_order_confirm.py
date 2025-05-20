from odoo import fields, models


class SaleOrderConfirm(models.TransientModel):
    _name = "sale.order.confirm"
    _description = "Sale Order Confirmation"

    sale_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=True,
    )

    def create_normal_order(self):
        """Create normal sale order from quotation"""
        self.ensure_one()
        order = self.sale_id.copy(self.sale_id._prepare_order_from_quotation())
        self.sale_id.order_id = order.id
        if self.sale_id.state == "draft":
            self.sale_id.action_done()
        return self.sale_id.open_duplicated_sale_order()

    def create_blanket_order(self):
        """Create blanket order from quotation"""
        self.ensure_one()
        return self._prepare_and_create_bo()

    def _prepare_and_create_bo(self):
        vals = self._prepare_bo_values()
        bo = self.env["sale.blanket.order"].create(vals)
        self.sale_id.blanket_order_id = bo.id
        return self._get_bo_action(bo)

    def _prepare_bo_values(self):
        sale_order = self.sale_id
        common_vals = self._get_common_fields(sale_order)
        quotation_data = self._get_quotation_data(sale_order)
        line_vals = self._prepare_bo_lines(sale_order)

        return {
            **common_vals,
            "isolated_quotation_id": sale_order.id,
            "line_ids": line_vals,
            "quotation_data_json": quotation_data,
        }

    def _get_common_fields(self, sale_order):
        sale_fields = self.env["sale.order"]._fields
        bo_fields = self.env["sale.blanket.order"]._fields
        common_fields = set(sale_fields.keys()) & set(bo_fields.keys())
        skip_fields = self._get_skip_fields()

        vals = {}
        for field in common_fields:
            if field not in skip_fields:
                value = getattr(sale_order, field)
                vals[field] = value.id if hasattr(value, "id") else value
        return vals

    def _get_quotation_data(self, sale_order):
        sale_fields = self.env["sale.order"]._fields
        bo_fields = self.env["sale.blanket.order"]._fields
        not_common = set(sale_fields.keys()) - set(bo_fields.keys())
        skip_fields = self._get_skip_fields()

        return {
            name: value
            for name, value in sale_order.read(not_common)[0].items()
            if name not in skip_fields and value
        }

    def _prepare_bo_lines(self, sale_order):
        bo_line_fields = self.env["sale.blanket.order.line"]._fields
        so_line_fields = self.env["sale.order.line"]._fields
        common_fields = set(bo_line_fields.keys()) & set(so_line_fields.keys())

        line_vals = []
        for line in sale_order.order_line:
            vals = {"order_id": False}
            for field in common_fields:
                value = getattr(line, field)
                vals[field] = value.id if hasattr(value, "id") else value
            vals["original_uom_qty"] = line.product_uom_qty
            line_vals.append((0, 0, vals))
        return line_vals

    def _get_skip_fields(self):
        return {
            "message_follower_ids",
            "message_ids",
            "__last_update",
            "message_partner_ids",
            "date_order",
            "expected_date",
            "name",
            "state",
            "display_type",
            "display_name",
            "access_url",
        }

    def _get_bo_action(self, bo):
        return {
            "type": "ir.actions.act_window",
            "name": "Blanket Order",
            "res_model": "sale.blanket.order",
            "view_mode": "form",
            "res_id": bo.id,
            "target": "current",
        }
