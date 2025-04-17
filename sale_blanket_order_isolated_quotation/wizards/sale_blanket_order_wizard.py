# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleBlanketOrderWizard(models.TransientModel):

    _inherit = "sale.blanket.order.wizard"

    quotation_data_json = fields.Json(
        related="blanket_order_id.quotation_data_json", string="Quotation Extra Data"
    )

    def _convert_datetime_if_needed(self, value):
        if isinstance(value, str):
            # Substitui 'T' por espaço, se for formato ISO
            value = value.replace("T", " ")
            try:
                # Valida o valor com strptime
                datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return value
            except ValueError:
                return value

    def _resolve_field_value(self, field_name, value):
        field = self._fields.get(field_name)
        if not field:
            return value
        if field.type == "many2one":
            if isinstance(value, str):
                match = self.env[field.comodel_name].name_search(value, limit=1)
                return match[0][0] if match else False
        elif field.type == "many2many":
            if isinstance(value, list):
                ids = []
                for val in value:
                    if isinstance(val, str):
                        match = self.env[field.comodel_name].name_search(val, limit=1)
                        if match:
                            ids.append(match[0][0])
                return [(6, 0, ids)] if ids else False
        elif field.type == "date":
            return self._convert_datetime_if_needed(value)
        return value

    @api.model
    def _check_valid_blanket_order_line(self, bo_lines):
        company_id = False
        for line in bo_lines:
            if line.order_id.state != "open":
                raise UserError(
                    _("Sale Blanket Order %s is not open") % line.order_id.name
                )
            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(_("You have to select lines " "from the same company."))
            else:
                company_id = line_company_id

    def _prepare_so_vals(
        self,
        customer,
        user_id,
        currency_id,
        pricelist_id,
        payment_term_id,
        order_lines_by_customer,
    ):
        vals = super()._prepare_so_vals(
            customer,
            user_id,
            currency_id,
            pricelist_id,
            payment_term_id,
            order_lines_by_customer,
        )

        extra_fields = self.quotation_data_json or {}
        for key in list(vals.keys()):
            extra_fields.pop(key, None)

        for field, value in extra_fields.items():
            if isinstance(value, list) and len(value) == 2:
                extra_fields[field] = value[0]

        extra_fields = {
            field: value
            for field, value in extra_fields.items()
            if not isinstance(value, dict)
        }
        vals.update(extra_fields)
        vals["isolated_blanket_order_id"] = self.blanket_order_id.id
        return vals

    @api.model
    def _default_lines(self):
        blanket_order_line_obj = self.env["sale.blanket.order.line"]
        blanket_order_line_ids = self.env.context.get("active_ids", False)
        active_model = self.env.context.get("active_model", False)

        if active_model == "sale.blanket.order":
            bo_lines = self._default_order().line_ids
        else:
            bo_lines = blanket_order_line_obj.browse(blanket_order_line_ids)

        self._check_valid_blanket_order_line(bo_lines)
        lines = [
            (
                0,
                0,
                {
                    "blanket_line_id": bol.id,
                    "product_id": bol.product_id.id,
                    "date_schedule": bol.date_schedule,
                    "remaining_uom_qty": bol.remaining_uom_qty,
                    "price_unit": bol.price_unit,
                    "product_uom": bol.product_uom,
                    "qty": bol.remaining_uom_qty,
                    "partner_id": bol.partner_id,
                },
            )
            for bol in bo_lines
        ]
        return lines

    def create_sale_order(self):
        res = super().create_sale_order()

        for sale_order in self.env["sale.order"].browse(res["domain"][0][2]):
            sale_order.action_confirm()

        return res
