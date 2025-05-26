# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import _, api, exceptions, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    blanket_order_type = fields.Selection(
        [
            ("none", "Normal Order"),
            ("reference", "B.O. Reference"),
            ("amendment", "B.O. Amendment"),
        ],
        string="B.O. Operation Type",
        default="none",
    )

    is_blanket_order_increment = fields.Boolean(
        readonly=True,
        copy=False,
    )

    blanket_order_id = fields.Many2one(
        comodel_name="sale.blanket.order",
        string="Related Blanket Order",
        states={"draft": [("readonly", False)]},
        copy=False,
        related="",
    )
    blanket_order_referenced_id = fields.Many2one(
        comodel_name="sale.blanket.order",
        string="Related Blanket Order",
        states={"draft": [("readonly", False)]},
        copy=False,
    )

    def action_confirm(self):
        """Override to handle blanket order operations"""
        self.ensure_one()
        if self.blanket_order_type == "reference":
            return self._confirm_blanket_order_reference()
        elif self.blanket_order_type == "amendment":
            return self._confirm_blanket_order_increment()
        elif not self.order_sequence:  # É um orçamento
            return {
                "name": _("Confirm Sale Order"),
                "type": "ir.actions.act_window",
                "res_model": "sale.order.confirm",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_sale_id": self.id,
                },
            }
        return super().action_confirm()

    def _confirm_blanket_order_reference(self):
        """Create sale order from B.O. reference and consume quantities"""
        self.ensure_one()
        self._validate_bo_quantities()
        return self._create_sale_from_reference()

    def _validate_bo_quantities(self):
        for line in self.order_line:
            if not line.blanket_order_line_id:
                continue
            available = line.blanket_order_line_id.remaining_qty
            if line.product_uom_qty > available:
                raise exceptions.ValidationError(
                    _(
                        "Requested quantity %(requested_qty)s exceeds available balance "
                        "%(available_qty)s for product %(product)s"
                    )
                    % {
                        "requested_qty": line.product_uom_qty,
                        "available_qty": available,
                        "product": line.product_id.name,
                    }
                )

    def _create_sale_from_reference(self):
        return self.blanket_order_id.create_sale_order_from_wizard(self.order_line)
        # sale_order_id = self.env["sale.order"].browse(
        #     sale_order.get("domain", [])[0][2][0]
        # )

        # # Update quantities based on reference
        # for line in sale_order_id.order_line:
        #     ref_line = self.order_line.filtered(
        #         lambda line_item: line_item.blanket_order_line_id
        #         == line.blanket_order_line_id
        #     )
        #     if ref_line:
        #         line.product_uom_qty = ref_line.product_uom_qty

        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "Sales Order",
        #     "res_model": "sale.order",
        #     "view_mode": "form",
        #     "res_id": sale_order_id.id,
        #     "target": "current",
        # }

    def _confirm_blanket_order_increment(self):
        self.ensure_one()
        # self.blanket_order_id
        # blanket_order.state = "draft"
        self._update_bo_quantities()
        # blanket_order.action_confirm()
        return self._get_bo_action()

    def _update_bo_quantities(self):
        for line in self.order_line:
            bo_line = line.blanket_order_line_id
            if bo_line:
                new_qty = bo_line.original_uom_qty + line.product_uom_qty
                if new_qty < 0:
                    raise exceptions.ValidationError(
                        _("Cannot decrease quantity below zero for product %s")
                        % line.product_id.name
                    )
                bo_line.original_uom_qty = new_qty

    def _get_bo_action(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Blanket Order",
            "res_model": "sale.blanket.order",
            "view_mode": "form",
            "res_id": self.blanket_order_id.id,
            "target": "current",
        }

    def _prepare_blanket_order_line_values(self, bo_line):
        """Prepare values for creating sale order line from blanket order line."""
        return {
            "product_id": bo_line.product_id.id,
            "product_uom": bo_line.product_uom.id,
            "price_unit": bo_line.price_unit,
            "original_bo_qty": bo_line.original_uom_qty,
            "product_uom_qty": 0.0,  # Default to 0
            "blanket_order_line_id": bo_line.id,
        }

    @api.onchange("blanket_order_id")
    def _onchange_blanket_order_id(self):
        """Fill order lines when blanket order is selected"""
        if self.blanket_order_id:
            # Clear existing lines
            self.order_line = [(5, 0, 0)]

            # Create new lines from blanket order
            lines = []
            for bo_line in self.blanket_order_id.line_ids:
                vals = self._prepare_blanket_order_line_values(bo_line)
                lines.append((0, 0, vals))
            self.order_line = lines


# order_id = fields.Many2one(
#         comodel_name="sale.order",
#         string="Order",
#         readonly=True,
#         ondelete="restrict",
#         copy=False,
#         help="For Quotation, this field references to its Sales Order",
#     )
