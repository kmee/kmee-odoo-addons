from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class StockIndustrializationCreate(models.TransientModel):
    _name = "stock.industrialization.create"
    _description = "Criar recebimento para industrialização"

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Pedido de venda",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="stock.industrialization.create.line",
        inverse_name="wizard_id",
        string="Insumos do cliente",
    )

    def _get_picking_type(self):
        picking_type = self.env["stock.picking.type"].search(
            [
                ("is_industrialization", "=", True),
                ("warehouse_id", "=", self.sale_id.warehouse_id.id),
            ],
            limit=1,
        ) or self.env["stock.picking.type"].search(
            [
                ("is_industrialization", "=", True),
                ("company_id", "=", self.sale_id.company_id.id),
            ],
            limit=1,
        )
        if not picking_type:
            raise UserError(
                self.env._(
                    "Não há tipo de operação de recebimento para industrialização "
                    "no armazém do pedido."
                )
            )
        return picking_type

    def action_create(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.quantity > 0)
        if not lines:
            raise UserError(self.env._("Informe ao menos um insumo e a quantidade."))
        sale = self.sale_id
        picking_type = self._get_picking_type()
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "fiscal_operation_id": picking_type.fiscal_operation_id.id,
                "partner_id": sale.partner_id.id,
                "owner_id": sale.partner_id.id,
                "origin": sale.name,
                "company_id": sale.company_id.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "group_id": sale.procurement_group_id.id,
                "sale_id": sale.id,
                "is_industrialization": True,
                "move_ids": [
                    Command.create(
                        {
                            "name": line.product_id.display_name,
                            "product_id": line.product_id.id,
                            "product_uom": line.uom_id.id,
                            "product_uom_qty": line.quantity,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": (
                                picking_type.default_location_dest_id.id
                            ),
                            "origin": sale.name,
                        }
                    )
                    for line in lines
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
        }


class StockIndustrializationCreateLine(models.TransientModel):
    _name = "stock.industrialization.create.line"
    _description = "Insumo do recebimento para industrialização"

    wizard_id = fields.Many2one(
        comodel_name="stock.industrialization.create",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Insumo",
        required=True,
        domain=[("type", "=", "consu")],
    )
    quantity = fields.Float(
        string="Quantidade",
        digits="Product Unit of Measure",
        default=1.0,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unidade",
        compute="_compute_uom_id",
        store=True,
        precompute=True,
        readonly=False,
        required=True,
    )

    @api.depends("product_id")
    def _compute_uom_id(self):
        for line in self:
            line.uom_id = line.product_id.uom_id
