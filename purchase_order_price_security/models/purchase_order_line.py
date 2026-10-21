# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"

    can_edit_price_purchase = fields.Boolean(
        string="Can Edit Price in Purchase",
        compute="_compute_can_edit_price_purchase",
    )

    def _compute_can_edit_price_purchase(self):
        can_edit = self.env.user.has_group(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )
        for line in self:
            line.can_edit_price_purchase = can_edit

    def _price_security_user_can_edit(self):
        return self.env.su or self.env.user.has_group(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )

    def _price_security_is_locked(self):
        """Lines whose unit price comes from the vendor pricelist or the cost."""
        self.ensure_one()
        return not self.display_type

    def _price_security_system_price(self):
        """Unit price the system computes for the line, without saving it."""
        self.ensure_one()
        line = self.sudo()
        # start from zero: the core keeps a price already on the line when
        # the vendor has no pricelist, which would accept any typed price
        virtual = line.new({"price_unit": 0.0}, origin=line)
        virtual._compute_price_unit_and_date_planned_and_name()
        return virtual.price_unit

    def _price_security_check(self, old_prices=None):
        """Refuse prices typed by users outside the price editor group.

        A price is accepted when it is unchanged or equal to the one the
        system computes, which is what internal flows send.
        """
        old_prices = old_prices or {}
        digits = self.env["decimal.precision"].precision_get("Product Price")
        for line in self.filtered(lambda rec: rec._price_security_is_locked()):
            old_price = old_prices.get(line.id)
            if (
                old_price is not None
                and float_compare(line.price_unit, old_price, precision_digits=digits)
                == 0
            ):
                continue
            system_price = line._price_security_system_price()
            if (
                float_compare(line.price_unit, system_price, precision_digits=digits)
                != 0
            ):
                raise AccessError(
                    _(
                        "You are not allowed to change the unit price of the "
                        "purchase order line %(line)s (%(price)s). Only members "
                        "of the group %(group)s can do it.",
                        line=line.display_name,
                        price=line.price_unit,
                        group=self.env.ref(
                            "purchase_order_price_security."
                            "group_purchase_order_price_editor"
                        ).name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self._price_security_user_can_edit():
            self.browse(
                line.id for line, vals in zip(lines, vals_list) if "price_unit" in vals
            )._price_security_check()
        return lines

    def write(self, vals):
        if "price_unit" not in vals or self._price_security_user_can_edit():
            return super().write(vals)
        old_prices = {line.id: line.price_unit for line in self}
        res = super().write(vals)
        self._price_security_check(old_prices)
        return res

    def copy_data(self, default=None):
        data_list = super().copy_data(default)
        if not self._price_security_user_can_edit():
            # the copy is priced again by the system, as a new line would be
            for line, data in zip(self, data_list):
                if line._price_security_is_locked() and "price_unit" not in (
                    default or {}
                ):
                    data.pop("price_unit", None)
        return data_list
