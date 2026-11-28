from odoo import Command, api, fields, models
from odoo.exceptions import UserError

MODULE = "l10n_br_stock_industrialization"

# operação de serviço -> (operação de retorno, linha do material não utilizado)
CONSIGNMENT_RETURN_OPERATIONS = {
    f"{MODULE}.fo_servico_industrializacao": (
        f"{MODULE}.fo_retorno_industrializacao",
        f"{MODULE}.fo_retorno_industrializacao_retorno_nao_utilizado",
    ),
    f"{MODULE}.fo_servico_industrializacao_conta_ordem": (
        f"{MODULE}.fo_retorno_ind_conta_ordem",
        f"{MODULE}.fol_retorno_ind_conta_ordem_retorno_nao_utilizado",
    ),
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_industrialization = fields.Boolean(
        string="Industrialização",
        compute="_compute_is_industrialization",
        store=True,
        readonly=False,
        precompute=True,
        copy=False,
        help="Recebimento do material do cliente para industrialização.",
    )
    merge_moves = fields.Boolean(
        string="Mesclar movimentos",
        default=True,
        copy=False,
        help="Ao confirmar, os movimentos do mesmo produto são mesclados em um.",
    )
    display_consignment_page = fields.Boolean(
        compute="_compute_display_consignment_page",
    )
    consignment_line_ids = fields.Many2many(
        comodel_name="stock.quant",
        string="Material do cliente em estoque",
        compute="_compute_consignment_line_ids",
    )
    to_return_consignment_line_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="consignment_picking_id",
        string="Lotes para devolução",
    )

    @api.depends("picking_type_id")
    def _compute_is_industrialization(self):
        for picking in self:
            picking.is_industrialization = picking.picking_type_id.is_industrialization

    def _consignment_operations(self):
        return self.env["l10n_br_fiscal.operation"].browse(
            [self.env.ref(xmlid).id for xmlid in CONSIGNMENT_RETURN_OPERATIONS]
        )

    @api.depends("fiscal_operation_id", "picking_type_id", "location_id")
    def _compute_display_consignment_page(self):
        operations = self._consignment_operations()
        for picking in self:
            picking.display_consignment_page = bool(
                picking.fiscal_operation_id in operations
                and picking.picking_type_id.code == "internal"
                and picking.location_id.usage == "internal"
                and picking.location_dest_id.usage == "internal"
            )

    @api.depends("display_consignment_page", "partner_id", "location_id")
    def _compute_consignment_line_ids(self):
        Quant = self.env["stock.quant"]
        for picking in self:
            quants = Quant
            if picking.display_consignment_page and picking.partner_id:
                quants = Quant.search(
                    [
                        ("owner_id", "in", picking._consignment_owners().ids),
                        ("location_id", "child_of", picking.location_id.id),
                        ("quantity", ">", 0),
                    ]
                ).filtered(lambda quant: quant.available_quantity > 0)
            picking.consignment_line_ids = quants

    def _consignment_return_operation(self):
        self.ensure_one()
        for service_xmlid, xmlids in CONSIGNMENT_RETURN_OPERATIONS.items():
            if self.fiscal_operation_id == self.env.ref(service_xmlid):
                return tuple(self.env.ref(xmlid) for xmlid in xmlids)
        raise UserError(
            self.env._(
                "A devolução de material não utilizado exige a operação de serviço "
                "de industrialização na separação."
            )
        )

    def _consignment_owners(self):
        self.ensure_one()
        return self.partner_id | self.partner_id.commercial_partner_id

    def action_set_sale(self):
        self.ensure_one()
        if self.sale_id:
            raise UserError(self.env._("Este recebimento já possui uma venda."))
        return self.env["ir.actions.actions"]._for_xml_id(
            f"{MODULE}.stock_industrialization_set_sale_action"
        )

    def action_create_consignment_return(self):
        self.ensure_one()
        if self.state in ("done", "cancel"):
            raise UserError(self.env._("A separação já está concluída ou cancelada."))
        operation, operation_line = self._consignment_return_operation()
        delivery = fields.first(
            self.sale_id.picking_ids.filtered(
                lambda p: p.state not in ("done", "cancel")
                and p.location_dest_id.usage == "customer"
            )
        )
        if not delivery:
            raise UserError(
                self.env._("A venda não tem entrega em aberto para receber o retorno.")
            )
        moves = self.env["stock.move"]
        for quant in self.to_return_consignment_line_ids:
            moves |= self._create_consignment_return_moves(
                quant, delivery, operation, operation_line
            )
        moves._action_confirm(merge=False)
        moves._recompute_state()
        self.to_return_consignment_line_ids.button_remove_from_consignment_return()

    def _create_consignment_return_moves(self, quant, delivery, operation, line):
        quantity = quant.return_quantity
        if quantity <= 0 or quantity > quant.available_quantity:
            raise UserError(
                self.env._(
                    "A quantidade a devolver de %s deve ser maior que zero e não "
                    "pode passar do disponível.",
                    quant.product_id.display_name,
                )
            )
        lot = quant.lot_id
        price = lot._get_origin_unit_price(quant.product_id, quant.product_uom_id)
        common = {
            "name": quant.product_id.display_name,
            "product_id": quant.product_id.id,
            "product_uom": quant.product_uom_id.id,
            "product_uom_qty": quantity,
            "price_unit": price,
            "origin_nfe_id": lot.origin_nfe_id.id,
            "origin_nfe_line_id": lot.origin_nfe_line_id.id,
            "company_id": self.company_id.id,
        }
        move = self.env["stock.move"].create(
            dict(
                common,
                picking_id=self.id,
                location_id=quant.location_id.id,
                location_dest_id=self.location_dest_id.id,
                restrict_partner_id=quant.owner_id.id,
                is_consignment_return=True,
            )
        )
        move._update_reserved_quantity(
            quantity,
            quant.location_id,
            lot_id=lot,
            package_id=quant.package_id,
            owner_id=quant.owner_id,
            strict=True,
        )
        delivery_move = self.env["stock.move"].create(
            dict(
                common,
                picking_id=delivery.id,
                location_id=self.location_dest_id.id,
                location_dest_id=delivery.location_dest_id.id,
                move_orig_ids=[Command.link(move.id)],
                invoice_state="2binvoiced",
                fiscal_operation_id=operation.id,
                fiscal_operation_line_id=line.id,
            )
        )
        return move | delivery_move

    def _action_done(self):
        self._check_lots_for_industrialization()
        self._check_owner_for_consignment_return()
        res = super()._action_done()
        self._set_lots_origin_sale()
        return res

    def _check_lots_for_industrialization(self):
        for picking in self.filtered("is_industrialization"):
            lines = picking.move_line_ids.filtered("quantity")
            for line in lines.filtered(lambda line: not line.lot_id):
                raise UserError(
                    self.env._(
                        "Informe o lote do produto %s: todo item do recebimento "
                        "para industrialização precisa de lote.",
                        line.product_id.display_name,
                    )
                )
            seen = set()
            for line in lines:
                if line.lot_id.id in seen:
                    raise UserError(
                        self.env._(
                            "Duas linhas do recebimento têm o mesmo produto e lote. "
                            "Os lotes da industrialização devem ser únicos: crie um "
                            "novo lote para uma das linhas.\n\nProduto: %s",
                            line.product_id.display_name,
                        )
                    )
                seen.add(line.lot_id.id)

    def _check_owner_for_consignment_return(self):
        for picking in self:
            owners = picking._consignment_owners()
            lines = picking.move_ids.filtered("is_consignment_return").move_line_ids
            for line in lines.filtered("quantity"):
                if not line.owner_id:
                    raise UserError(
                        self.env._("Devoluções de material do cliente exigem dono.")
                    )
                if line.owner_id not in owners:
                    raise UserError(
                        self.env._(
                            "O material selecionado para devolução não pertence ao "
                            "parceiro desta separação."
                        )
                    )

    def _set_lots_origin_sale(self):
        """Lotes recebidos ficam reservados à venda de origem."""
        for picking in self.filtered(
            lambda p: p.is_industrialization and p.state == "done" and p.sale_id
        ):
            picking.move_line_ids.lot_id.write({"origin_sale_id": picking.sale_id.id})
