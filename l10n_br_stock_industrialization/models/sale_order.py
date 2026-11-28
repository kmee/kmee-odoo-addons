from odoo import api, fields, models
from odoo.exceptions import UserError

MODULE = "l10n_br_stock_industrialization"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    industrialization_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Recebimentos para industrialização",
        compute="_compute_industrialization_ids",
    )
    industrialization_count = fields.Integer(
        string="Recebimentos para industrialização",
        compute="_compute_industrialization_ids",
    )

    @api.depends("picking_ids.is_industrialization")
    def _compute_industrialization_ids(self):
        for order in self:
            order.industrialization_ids = order.picking_ids.filtered(
                "is_industrialization"
            )
            order.industrialization_count = len(order.industrialization_ids)

    @api.depends("picking_ids.is_industrialization")
    def _compute_picking_ids(self):
        res = super()._compute_picking_ids()
        for order in self:
            order.delivery_count = len(order.picking_ids - order.industrialization_ids)
        return res

    @api.model
    def _billing_only_operations(self):
        """Operações em que a rota "Apenas cobrança" é permitida."""
        return self.env.ref(f"{MODULE}.fo_servico_industrializacao") | self.env.ref(
            f"{MODULE}.fo_servico_industrializacao_conta_ordem"
        )

    @api.constrains("fiscal_operation_id")
    def _check_billing_only_route(self):
        self.order_line._check_billing_only_route()

    def action_create_industrialization(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            f"{MODULE}.stock_industrialization_create_action"
        )
        action["context"] = {"default_sale_id": self.id}
        return action

    def action_view_industrialization(self):
        self.ensure_one()
        return self._get_action_view_picking(self.industrialization_ids)

    def action_view_delivery(self):
        self.ensure_one()
        return self._get_action_view_picking(
            self.picking_ids - self.industrialization_ids
        )

    def _action_confirm(self):
        res = super()._action_confirm()
        operations = self._billing_only_operations()
        for order in self.filtered(lambda o: o.fiscal_operation_id in operations):
            # as etapas intermediárias da entrega seguem a operação do pedido
            (order.picking_ids - order.industrialization_ids).write(
                {"fiscal_operation_id": order.fiscal_operation_id.id}
            )
        return res

    def _action_cancel(self):
        if any(picking.state != "cancel" for picking in self.industrialization_ids):
            raise UserError(
                self.env._(
                    "Não é possível cancelar a venda com recebimentos para "
                    "industrialização em aberto."
                )
            )
        return super()._action_cancel()
