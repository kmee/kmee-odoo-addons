from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    is_consignment_return = fields.Boolean(
        string="Devolução de material não utilizado",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # A rota "Apenas cobrança" fatura a venda sem movimentar o estoque: o
        # movimento que a regra de abastecimento criaria é descartado.
        route = self.env.ref(
            "l10n_br_stock_industrialization.route_apenas_cobranca",
            raise_if_not_found=False,
        )
        if route:
            vals_list = [
                vals
                for vals in vals_list
                if route.id not in self._route_ids_from_commands(vals)
            ]
            if not vals_list:
                return self.browse()
        return super().create(vals_list)

    @api.model
    def _route_ids_from_commands(self, vals):
        route_ids = []
        for command in vals.get("route_ids") or []:
            if not isinstance(command, list | tuple):
                continue
            if command[0] in (4, 1) and len(command) > 1:
                route_ids.append(command[1])
            elif command[0] == 6 and len(command) > 2:
                route_ids.extend(command[2])
        return route_ids

    def _action_confirm(self, merge=True, merge_into=False):
        pickings = self.picking_id
        if pickings and not any(pickings.mapped("merge_moves")):
            merge = False
        return super()._action_confirm(merge=merge, merge_into=merge_into)

    def unlink(self):
        returns = self.filtered(
            lambda move: move.is_consignment_return
            and move.state not in ("draft", "cancel", "done")
        )
        if returns:
            # o retorno ainda não concluído pode ser removido: libera a reserva
            # e o movimento seguinte da entrega
            destinations = returns.move_dest_ids.filtered(
                lambda move: move.state != "done"
            )
            returns.move_line_ids.unlink()
            (returns | destinations).write({"state": "draft"})
            destinations.unlink()
        return super().unlink()
