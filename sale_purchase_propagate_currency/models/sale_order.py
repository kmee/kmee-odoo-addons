# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        """
        When confirming a Sale Order, ensure MTO POs have the same currency as the SO.
        Recompute prices on PO lines accordingly.
        This must be done with with_company to ensure the specific company's pricelist "
        "will be used.
        proper access rights.
        Sudo is used to read the SO and PO data, as inter-company users may not have
        the required access rights.
        """
        res = super()._action_confirm()

        for order in self:
            if (
                not order.company_id
            ):  # if company_id not found, return to normal behavior
                continue
            # recompute prices as SO specific company
            po_ids = order.sudo().with_company(order.company_id)._get_purchase_orders()

            for po in po_ids:
                if order.currency_id != po.currency_id:
                    po.currency_id = order.currency_id
                    # Recompute prices on PO lines
                    for line in po.order_line:
                        line.sudo().with_company(order.company_id)._onchange_quantity()
        return res
