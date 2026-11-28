from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_stock_move_values(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
    ):
        move_values = super()._get_stock_move_values(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
        )
        # Only the MTS leg of an MTS+MTO rule: it is the one that takes from stock
        if self._is_mts_leg_of_mts_mto_rule() and (
            values.get("sale_line_id")
            or values.get("move_dest_ids", self.env["stock.move"]).sale_line_id
        ):
            move_values["pulled_from_stock"] = True
        return move_values

    def _is_mts_leg_of_mts_mto_rule(self):
        self.ensure_one()
        return bool(
            self.env["stock.rule"].search_count(
                [("action", "=", "split_procurement"), ("mts_rule_id", "=", self.id)],
                limit=1,
            )
        )

    def _get_custom_move_fields(self):
        res = super()._get_custom_move_fields()
        res.append("pulled_from_stock")
        return res
