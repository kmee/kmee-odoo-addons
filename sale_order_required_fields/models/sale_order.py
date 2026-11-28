from odoo import fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_require_payment_mode = fields.Boolean(
        related="company_id.sale_require_payment_mode"
    )
    sale_require_payment_term = fields.Boolean(
        related="company_id.sale_require_payment_term"
    )
    sale_require_line_date = fields.Boolean(related="company_id.sale_require_line_date")

    def _check_required_fields(self):
        """The views mark the fields as required, this also covers imports and RPC."""
        for order in self:
            missing = []
            if order.sale_require_payment_mode and not order.payment_mode_id:
                missing.append(self._fields["payment_mode_id"].string)
            if order.sale_require_payment_term and not order.payment_term_id:
                missing.append(self._fields["payment_term_id"].string)
            if order.sale_require_line_date and any(
                not line.commitment_date
                for line in order.order_line
                if not line.display_type
            ):
                missing.append(
                    self.env["sale.order.line"]._fields["commitment_date"].string
                )
            if missing:
                raise ValidationError(
                    self.env._(
                        "Order %(order)s: fill in the required fields: %(fields)s",
                        order=order.name,
                        fields=", ".join(missing),
                    )
                )

    def action_confirm(self):
        self._check_required_fields()
        return super().action_confirm()
