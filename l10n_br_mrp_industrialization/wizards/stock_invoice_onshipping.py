from odoo import api, models

MODULE = "l10n_br_stock_industrialization"

# operação do serviço -> (linha do retorno do material utilizado, linha do
# serviço sobre a matéria-prima aplicada)
INDUSTRIALIZATION_LINES = {
    f"{MODULE}.fo_servico_industrializacao": (
        f"{MODULE}.fo_retorno_industrializacao_retorno_utilizado",
        f"{MODULE}.fol_servico_industrializacao_mat_prima",
    ),
    f"{MODULE}.fo_servico_industrializacao_conta_ordem": (
        f"{MODULE}.fol_retorno_ind_conta_ordem_retorno_utilizado",
        f"{MODULE}.fol_servico_ind_conta_ordem_mat_prima",
    ),
}


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _build_invoice_values_from_pickings(self, pickings):
        invoice, values = super()._build_invoice_values_from_pickings(pickings)
        # a criação da fatura só recebe os valores: as separações seguem junto
        values["industrialization_picking_ids"] = pickings.ids
        return invoice, values

    def _create_invoice(self, invoice_values):
        picking_ids = invoice_values.pop("industrialization_picking_ids", [])
        invoice = super()._create_invoice(invoice_values)
        pickings = self.env["stock.picking"].browse(picking_ids)
        lines = self._get_industrialization_invoice_lines(pickings)
        if lines:
            invoice.write({"invoice_line_ids": [(0, 0, line) for line in lines]})
        return invoice

    def _get_industrialization_operation_lines(self, picking):
        """Linhas de operação (retorno utilizado, serviço sobre a matéria-prima)
        da operação do serviço de industrialização da separação."""
        for service_xmlid, line_xmlids in INDUSTRIALIZATION_LINES.items():
            if picking.fiscal_operation_id == self.env.ref(service_xmlid):
                return tuple(self.env.ref(xmlid) for xmlid in line_xmlids)
        return ()

    def _get_industrialization_invoice_lines(self, pickings):
        """Linhas do retorno do material utilizado (do cliente) e do serviço sobre
        a matéria-prima aplicada, das ordens de produção das separações de
        serviço de industrialização. Linhas iguais são agrupadas."""
        groups = {}
        for picking in pickings:
            operation_lines = self._get_industrialization_operation_lines(picking)
            if not operation_lines:
                continue
            return_line, service_line = operation_lines
            consumed, applied = self._get_industrialization_move_lines(picking)
            for move_line in consumed:
                price = self._get_consumed_price(move_line)
                self._add_industrialization_line(groups, move_line, price, return_line)
            for move_line in applied:
                price = self._get_applied_price(picking, move_line)
                self._add_industrialization_line(groups, move_line, price, service_line)
        return list(groups.values())

    @api.model
    def _get_origin_productions(self, picking):
        """Ordens de produção que originaram as entregas da separação."""
        productions = self.env["mrp.production"]
        seen = self.env["stock.move"]
        moves = picking.move_ids
        while moves:
            seen |= moves
            productions |= moves.production_id
            moves = moves.move_orig_ids - seen
        return productions.filtered(lambda p: p.state != "cancel")

    def _get_industrialization_move_lines(self, picking):
        """Consumos concluídos e ainda não faturados das ordens de produção da
        separação: (material do cliente consumido, matéria-prima aplicada da
        empresa). Os consumos devolvidos ficam marcados como faturados."""
        raw_moves = self._get_origin_productions(picking).move_raw_ids.filtered(
            lambda m: m.state == "done" and not m.has_been_invoiced_industrialization
        )
        customer = picking.partner_id.commercial_partner_id
        consumed = self.env["stock.move.line"]
        applied = self.env["stock.move.line"]
        for move_line in raw_moves.move_line_ids.filtered("quantity"):
            if (
                move_line.owner_id
                and move_line.owner_id.commercial_partner_id == customer
            ):
                consumed |= move_line
            else:
                applied |= move_line
        raw_moves.has_been_invoiced_industrialization = True
        return consumed, applied

    @api.model
    def _get_consumed_price(self, move_line):
        """Preço do material do cliente: o da linha da nota de origem do lote."""
        product = move_line.product_id
        if not move_line.lot_id:
            return product.standard_price
        return move_line.lot_id._get_origin_unit_price(product, product.uom_id)

    @api.model
    def _get_applied_price(self, picking, move_line):
        """Preço da matéria-prima aplicada: o da linha do pedido de venda na rota
        Apenas cobrança."""
        route = self.env.ref(f"{MODULE}.route_apenas_cobranca")
        order_line = picking.sale_id.order_line.filtered(
            lambda line: line.route_id == route
            and line.product_id == move_line.product_id
        )[:1]
        return order_line.price_unit

    def _add_industrialization_line(self, groups, move_line, price, operation_line):
        product = move_line.product_id
        key = (product.id, price, operation_line.id)
        quantity = move_line.quantity_product_uom
        move = move_line.move_id
        if key not in groups:
            groups[key] = {
                "name": product.name,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": 0,
                "fiscal_quantity": 0,
                "price_unit": price,
                "fiscal_price": price,
                "fiscal_operation_id": operation_line.fiscal_operation_id.id,
                "fiscal_operation_line_id": operation_line.id,
                "origin_mo_move_line_ids": [],
            }
        values = groups[key]
        values["quantity"] += quantity
        values["fiscal_quantity"] = values["quantity"]
        if (4, move.id) not in values["origin_mo_move_line_ids"]:
            values["origin_mo_move_line_ids"].append((4, move.id))
