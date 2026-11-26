# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        return super()._get_custom_move_fields() + [
            "created_after_sale_order_confirmed"
        ]

    @api.model
    def _is_component_procurement(self, procurement):
        """The procurement was triggered by a component move of a manufacturing
        order."""
        move_dest = procurement.values.get("move_dest_ids")
        return bool(move_dest and move_dest[0].raw_material_production_id)

    def _need_production_request(self, product_id, action="manufacture"):
        if self.env.context.get("mrp_production_request_sale_skip"):
            return False
        return super()._need_production_request(product_id, action=action)

    @api.model
    def _run_manufacture(self, procurements):
        sub_procurements = []
        other_procurements = []
        for procurement, rule in procurements:
            if self._is_component_procurement(procurement):
                procurement.values["is_sub_mo"] = True
                sub_procurements.append((procurement, rule))
            else:
                other_procurements.append((procurement, rule))
        res = super()._run_manufacture(other_procurements)
        if sub_procurements:
            # A manufactured component goes straight to a manufacturing order,
            # without a production request of its own.
            super(
                StockRule,
                self.with_context(mrp_production_request_sale_skip=True),
            )._run_manufacture(sub_procurements)
        return res

    def _prepare_mo_vals(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        bom,
    ):
        res = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        if values.get("is_sub_mo"):
            res["is_sub_mo"] = True
        return res
