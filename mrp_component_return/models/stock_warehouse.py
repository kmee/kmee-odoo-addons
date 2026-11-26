from odoo import _, api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    component_return_enabled = fields.Boolean(
        string="Return Components",
        help="Allow returning to stock the components picked for a manufacturing"
        " order and not consumed. The manufacturing order cannot be cancelled or"
        " done while components are left in pre-production.",
    )
    component_return_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Component Return Operation Type",
        check_company=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        warehouses._setup_component_return_type()
        return warehouses

    def write(self, vals):
        res = super().write(vals)
        if {"component_return_enabled", "manufacture_steps", "active"} & vals.keys():
            self._setup_component_return_type()
        return res

    def _component_return_active(self):
        self.ensure_one()
        return (
            self.component_return_enabled
            and self.manufacture_steps != "mrp_one_step"
            and self.active
        )

    def _prepare_component_return_type_vals(self):
        self.ensure_one()
        return {
            "name": _("Return Components"),
            "code": "internal",
            "sequence_code": "RPC",
            "warehouse_id": self.id,
            "company_id": self.company_id.id,
            "default_location_src_id": self.pbm_loc_id.id,
            "default_location_dest_id": self.lot_stock_id.id,
        }

    def _setup_component_return_type(self):
        """Create the return operation type (pre-production to stock) and link
        it as the return of the component picking type."""
        for warehouse in self:
            return_type = warehouse.component_return_type_id
            if not warehouse.component_return_enabled:
                if return_type:
                    return_type.active = False
                continue
            if not return_type and warehouse.pbm_loc_id:
                return_type = (
                    self.env["stock.picking.type"]
                    .with_context(active_test=False)
                    .create(warehouse._prepare_component_return_type_vals())
                )
                warehouse.component_return_type_id = return_type
            if not return_type:
                continue
            return_type.active = warehouse._component_return_active()
            if warehouse.pbm_type_id:
                warehouse.pbm_type_id.return_picking_type_id = return_type
