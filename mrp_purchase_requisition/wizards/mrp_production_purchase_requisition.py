# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpProductionPurchaseRequisition(models.TransientModel):
    _name = "mrp.production.purchase.requisition"
    _description = "Create a purchase agreement from a manufacturing order"

    production_id = fields.Many2one(
        comodel_name="mrp.production",
        required=True,
        readonly=True,
    )
    schedule_date = fields.Date(string="Schedule in the Future")
    is_first_requisition = fields.Boolean(
        compute="_compute_is_first_requisition",
    )
    justificativa = fields.Text(
        string="Justification",
        help="Required when the manufacturing order already has a purchase "
        "agreement.",
    )
    line_ids = fields.One2many(
        comodel_name="mrp.production.purchase.requisition.line",
        inverse_name="wizard_id",
        string="Components",
    )

    @api.depends("production_id.requisition_count")
    def _compute_is_first_requisition(self):
        for wizard in self:
            wizard.is_first_requisition = not wizard.production_id.requisition_count

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        production = self.env["mrp.production"].browse(
            self.env.context.get("default_production_id")
            or self.env.context.get("active_id")
        )
        res["production_id"] = production.id
        res["line_ids"] = [
            (0, 0, self._prepare_wizard_line(move))
            for move in production.move_raw_ids.filtered(
                lambda move: move.state not in ("done", "cancel")
            )
            if self._missing_qty(move) > 0
        ]
        return res

    @api.model
    def _missing_qty(self, move):
        """Demand of the component move that is not reserved yet."""
        return move.product_uom_qty - move.quantity

    @api.model
    def _prepare_wizard_line(self, move):
        return {
            "product_id": move.product_id.id,
            "product_uom_id": move.product_uom.id,
            "product_qty": self._missing_qty(move),
            "missing_qty": self._missing_qty(move),
        }

    def _prepare_requisition_line(self, line):
        return {
            "product_id": line.product_id.id,
            "product_uom_id": line.product_uom_id.id,
            "product_qty": line.product_qty,
            "schedule_date": self.schedule_date,
            "production_id": self.production_id.id,
            "justificativa": self.justificativa,
        }

    def create_purchase_requisition(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.product_qty > 0)
        if not lines:
            raise UserError(_("There is no quantity to request."))
        if not self.is_first_requisition and not self.justificativa:
            raise UserError(
                _(
                    "The manufacturing order already has a purchase agreement. "
                    "Inform the justification for a new one."
                )
            )
        requisition = self.env["purchase.requisition"].create(
            {
                "requisition_type": "purchase_template",
                "procurement_group_id": self.production_id.procurement_group_id.id,
                "line_ids": [
                    (0, 0, self._prepare_requisition_line(line)) for line in lines
                ],
            }
        )
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_requisition.action_purchase_requisition"
        )
        action.update(
            {
                "res_id": requisition.id,
                "views": [(False, "form")],
                "view_mode": "form",
            }
        )
        return action


class MrpProductionPurchaseRequisitionLine(models.TransientModel):
    _name = "mrp.production.purchase.requisition.line"
    _description = "Component line of the purchase agreement wizard"

    wizard_id = fields.Many2one(
        comodel_name="mrp.production.purchase.requisition",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        readonly=True,
    )
    missing_qty = fields.Float(
        string="Missing Quantity",
        digits="Product Unit of Measure",
        readonly=True,
    )
    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure",
    )
    below_missing = fields.Boolean(compute="_compute_below_missing")

    @api.depends("product_qty", "missing_qty")
    def _compute_below_missing(self):
        for line in self:
            line.below_missing = (
                float_compare(
                    line.product_qty,
                    line.missing_qty,
                    precision_rounding=line.product_uom_id.rounding or 0.01,
                )
                < 0
            )
