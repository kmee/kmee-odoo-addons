from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VanSession(models.Model):
    _name = "van.session"
    _description = "Van Sales Session"
    _order = "date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="/")
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("loaded", "Carregado"),
            ("in_route", "Em Rota"),
            ("returned", "Retornado"),
            ("closed", "Fechado"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    date_close = fields.Date(string="Data Fechamento", readonly=True, copy=False)
    driver_id = fields.Many2one(
        "res.partner",
        required=True,
        domain="[('is_van_driver', '=', True)]",
    )
    pos_config_id = fields.Many2one(
        "pos.config",
        required=True,
        domain="[('is_van_config', '=', True)]",
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de Preços",
        compute="_compute_pricelist_id",
        store=True,
        readonly=False,
    )

    @api.depends("pos_config_id")
    def _compute_pricelist_id(self):
        for session in self:
            if session.pos_config_id.pricelist_id:
                session.pricelist_id = session.pos_config_id.pricelist_id
            elif not session.pricelist_id:
                session.pricelist_id = False

    pos_session_id = fields.Many2one("pos.session", readonly=True, copy=False)
    load_picking_id = fields.Many2one(
        "stock.picking", string="Picking de Carga", copy=False
    )
    unload_picking_id = fields.Many2one(
        "stock.picking", string="Picking de Descarga", readonly=True, copy=False
    )
    line_ids = fields.One2many("van.session.line", "session_id", copy=True)
    move_id = fields.Many2one(
        "account.move", string="Lançamento de Fechamento", readonly=True, copy=False
    )
    cash_diff = fields.Monetary(string="Diferença de Caixa", readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    total_qty_out = fields.Float(
        string="Total Saída", compute="_compute_totals", store=True
    )
    total_qty_sold = fields.Float(
        string="Total Vendido", compute="_compute_totals", store=True
    )
    total_qty_returned = fields.Float(
        string="Total Retornado", compute="_compute_totals", store=True
    )
    total_qty_diff = fields.Float(
        string="Total Diferença", compute="_compute_totals", store=True
    )
    total_qty_keep = fields.Float(
        string="Total Manter", compute="_compute_totals", store=True
    )
    total_amount = fields.Monetary(
        string="Dif. Carga", compute="_compute_totals", store=True
    )
    total_diff = fields.Monetary(
        string="Dif. Total", compute="_compute_totals", store=True
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Armazém Caminhão",
        compute="_compute_warehouse_id",
        store=True,
    )

    @api.depends("pos_config_id.van_load_picking_type_id")
    def _compute_warehouse_id(self):
        for session in self:
            pt = session.pos_config_id.van_load_picking_type_id
            if pt and pt.default_location_dest_id:
                session.warehouse_id = pt.default_location_dest_id.warehouse_id
            else:
                session.warehouse_id = False

    @api.depends(
        "line_ids.qty_out",
        "line_ids.qty_sold",
        "line_ids.qty_returned",
        "line_ids.qty_diff",
        "line_ids.qty_keep",
        "line_ids.amount",
        "line_ids.waived",
        "cash_diff",
    )
    def _compute_totals(self):
        for session in self:
            lines = session.line_ids
            session.total_qty_out = sum(lines.mapped("qty_out"))
            session.total_qty_sold = sum(lines.mapped("qty_sold"))
            session.total_qty_returned = sum(lines.mapped("qty_returned"))
            session.total_qty_diff = sum(lines.mapped("qty_diff"))
            session.total_qty_keep = sum(lines.mapped("qty_keep"))
            session.total_amount = sum(ln.amount for ln in lines if not ln.waived)
            session.total_diff = session.total_amount + abs(
                session.cash_diff if session.cash_diff < 0 else 0
            )

    pos_order_ids = fields.One2many(
        related="pos_session_id.order_ids", string="Pedidos POS"
    )
    pos_payment_ids = fields.One2many(
        "pos.payment",
        compute="_compute_pos_payment_ids",
        string="Pagamentos POS",
    )

    @api.depends("pos_order_ids.payment_ids")
    def _compute_pos_payment_ids(self):
        for session in self:
            session.pos_payment_ids = session.pos_order_ids.payment_ids

    @api.constrains("driver_id", "state")
    def _check_unique_active_driver(self):
        active_states = ("loaded", "in_route", "returned")
        for rec in self:
            if rec.state not in active_states:
                continue
            domain = [
                ("driver_id", "=", rec.driver_id.id),
                ("state", "in", active_states),
                ("id", "!=", rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _("O motorista %s já possui uma sessão ativa.")
                    % rec.driver_id.display_name
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("van.session")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Path A: existing picking linked via load_picking_id
    # ------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if "load_picking_id" in vals:
            self.filtered("load_picking_id")._on_load_picking_linked()
        return res

    def _on_load_picking_linked(self):
        """Create van.session.line from linked picking's move lines."""
        for session in self:
            picking = session.load_picking_id
            if not picking:
                continue
            picking.write(
                {
                    "van_session_id": session.id,
                    "van_type": "load",
                }
            )
            existing_products = session.line_ids.mapped("product_id")
            lines_vals = []
            for move in picking.move_ids:
                if move.product_id in existing_products:
                    continue
                pricelist = session.pricelist_id
                if pricelist:
                    price = pricelist._get_product_price(
                        move.product_id, move.product_qty
                    )
                else:
                    price = move.product_id.lst_price
                lines_vals.append(
                    {
                        "session_id": session.id,
                        "product_id": move.product_id.id,
                        "qty_out": sum(move.move_line_ids.mapped("quantity")),
                        "out_move_line_ids": [(6, 0, move.move_line_ids.ids)],
                        "price_unit": price,
                    }
                )
            if lines_vals:
                self.env["van.session.line"].create(lines_vals)

    # ------------------------------------------------------------------
    # Load residual stock from van warehouse
    # ------------------------------------------------------------------

    def action_load_from_stock(self):
        """Load lines from current stock in the van warehouse."""
        for session in self:
            if session.state != "draft":
                raise UserError(
                    _("Só é possível carregar estoque em sessões rascunho.")
                )
            picking_type = session.pos_config_id.van_load_picking_type_id
            if not picking_type or not picking_type.default_location_dest_id:
                raise UserError(
                    _("Configure o tipo de picking de carga no POS %s.")
                    % session.pos_config_id.display_name
                )
            van_location = picking_type.default_location_dest_id
            # Find all quants in the van location (and children)
            quants = self.env["stock.quant"].search(
                [
                    ("location_id", "child_of", van_location.id),
                    ("quantity", ">", 0),
                ]
            )
            existing_products = session.line_ids.mapped("product_id")
            lines_vals = []
            for quant_group in quants.grouped("product_id").values():
                product = quant_group[0].product_id
                qty = sum(quant_group.mapped("quantity"))
                if qty <= 0:
                    continue
                pricelist = session.pricelist_id
                if pricelist:
                    price = pricelist._get_product_price(product, qty)
                else:
                    price = product.lst_price
                if product in existing_products:
                    # Update existing line
                    existing_line = session.line_ids.filtered(
                        lambda ln, p=product: ln.product_id == p
                    )
                    existing_line.write(
                        {
                            "qty_initial": qty,
                            "qty_out": qty
                            + (existing_line.qty_out - existing_line.qty_initial),
                        }
                    )
                else:
                    lines_vals.append(
                        {
                            "session_id": session.id,
                            "product_id": product.id,
                            "qty_initial": qty,
                            "qty_out": qty,
                            "price_unit": price,
                        }
                    )
            if lines_vals:
                self.env["van.session.line"].create(lines_vals)

    # ------------------------------------------------------------------
    # Path B: manual lines → create and validate picking
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Create load picking from manual lines, validate, state → loaded."""
        for session in self:
            if session.state != "draft":
                raise UserError(_("Só é possível confirmar sessões em rascunho."))
            if not session.line_ids:
                raise UserError(_("Adicione pelo menos uma linha antes de confirmar."))
            picking_type = session.pos_config_id.van_load_picking_type_id
            if not picking_type:
                raise UserError(
                    _("Configure o tipo de picking de carga no POS %s.")
                    % session.pos_config_id.display_name
                )
            # Only create picking for lines that need new stock from WH
            lines_to_load = session.line_ids.filtered(
                lambda ln: ln.qty_out - ln.qty_initial > 0
            )
            if lines_to_load:
                picking = self.env["stock.picking"].create(
                    {
                        "picking_type_id": picking_type.id,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": picking_type.default_location_dest_id.id,
                        "van_session_id": session.id,
                        "van_type": "load",
                        "origin": session.name,
                    }
                )
                for line in lines_to_load:
                    qty_to_load = line.qty_out - line.qty_initial
                    move = self.env["stock.move"].create(
                        {
                            "name": line.product_id.display_name,
                            "product_id": line.product_id.id,
                            "product_uom_qty": qty_to_load,
                            "product_uom": line.product_id.uom_id.id,
                            "picking_id": picking.id,
                            "location_id": picking.location_id.id,
                            "location_dest_id": picking.location_dest_id.id,
                        }
                    )
                    move._action_confirm()
                picking.action_assign()
                # Set done quantities
                for ml in picking.move_line_ids:
                    ml.quantity = ml.quantity_product_uom
                picking.move_ids.picked = True
                picking.button_validate()
                session.load_picking_id = picking
                # Link move lines back to session lines
                for line in lines_to_load:
                    move_lines = picking.move_line_ids.filtered(
                        lambda ml, p=line.product_id: ml.product_id == p
                    )
                    line.out_move_line_ids = [(6, 0, move_lines.ids)]
            session.state = "loaded"

    # ------------------------------------------------------------------
    # State revert actions
    # ------------------------------------------------------------------

    def action_back_to_draft(self):
        """Revert loaded → draft, cancel load picking."""
        for session in self:
            if session.state != "loaded":
                raise UserError(
                    _("Só é possível voltar ao rascunho a partir de 'Carregado'.")
                )
            if session.load_picking_id and session.load_picking_id.state == "done":
                session.load_picking_id.action_cancel()
            session.load_picking_id = False
            for line in session.line_ids:
                line.out_move_line_ids = [(5, 0, 0)]
            session.state = "draft"

    def action_back_to_loaded(self):
        """Revert returned → loaded, remove unload picking and sale links."""
        for session in self:
            if session.state != "returned":
                raise UserError(
                    _("Só é possível voltar a 'Carregado' a partir de 'Retornado'.")
                )
            if session.unload_picking_id:
                if session.unload_picking_id.state != "done":
                    session.unload_picking_id.action_cancel()
                session.unload_picking_id = False
            for line in session.line_ids:
                line.sale_move_line_ids = [(5, 0, 0)]
                line.in_move_line_ids = [(5, 0, 0)]
            session.cash_diff = 0
            session.state = "loaded"

    # ------------------------------------------------------------------
    # Open POS from van session
    # ------------------------------------------------------------------

    def action_open_pos(self):
        """Open POS UI for the linked pos.config, auto-linking sessions."""
        self.ensure_one()
        if self.state != "loaded":
            raise UserError(_("Só é possível abrir o POS com sessão carregada."))
        return self.pos_config_id.open_ui()

    # ------------------------------------------------------------------
    # POS session closed callback
    # ------------------------------------------------------------------

    def _on_pos_session_closed(self):
        """Called when the linked POS session is validated/closed."""
        for session in self:
            session._create_session_lines()
            session.cash_diff = session.pos_session_id.cash_register_difference
            session.state = "returned"

    def _create_unload_picking(self):
        """Create return picking with expected quantities."""
        self.ensure_one()
        picking_type = self.pos_config_id.van_unload_picking_type_id
        if not picking_type:
            raise UserError(
                _("Configure o tipo de picking de descarga no POS %s.")
                % self.pos_config_id.display_name
            )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "van_session_id": self.id,
                "van_type": "unload",
                "origin": self.name,
            }
        )
        for line in self.line_ids:
            expected_return = line.qty_out - line.qty_sold - line.qty_keep
            if expected_return <= 0:
                continue
            self.env["stock.move"].create(
                {
                    "name": line.product_id.display_name,
                    "product_id": line.product_id.id,
                    "product_uom_qty": expected_return,
                    "product_uom": line.product_id.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                }
            )
        if picking.move_ids:
            picking.action_confirm()
            picking.action_assign()
        self.unload_picking_id = picking

    def _create_session_lines(self):
        """Create/update session lines from POS session's pickings."""
        self.ensure_one()
        pos_session = self.pos_session_id
        if not pos_session:
            return
        # Gather sale move lines from POS pickings
        pos_pickings = self.env["stock.picking"].search(
            [
                ("pos_session_id", "=", pos_session.id),
            ]
        )
        sale_move_lines = pos_pickings.mapped("move_ids.move_line_ids")
        for line in self.line_ids:
            product_smls = sale_move_lines.filtered(
                lambda ml, p=line.product_id: ml.product_id == p
            )
            if product_smls:
                line.sale_move_line_ids = [(6, 0, product_smls.ids)]

    # ------------------------------------------------------------------
    # Unload validated callback
    # ------------------------------------------------------------------

    def _update_in_move_lines(self):
        """Populate in_move_line_ids after unload picking is validated."""
        for session in self:
            if not session.unload_picking_id:
                continue
            in_move_lines = session.unload_picking_id.move_ids.mapped("move_line_ids")
            for line in session.line_ids:
                product_mls = in_move_lines.filtered(
                    lambda ml, p=line.product_id: ml.product_id == p
                )
                if product_mls:
                    line.in_move_line_ids = [(6, 0, product_mls.ids)]

    # ------------------------------------------------------------------
    # Close / post journal entry
    # ------------------------------------------------------------------

    def _auto_validate_unload_picking(self):
        """Validate unload picking if assigned but not yet done."""
        self.ensure_one()
        picking = self.unload_picking_id
        if not picking or picking.state == "done" or not picking.move_ids:
            return
        if picking.state in ("confirmed", "assigned"):
            picking.action_assign()
            for ml in picking.move_line_ids:
                if not ml.quantity:
                    ml.quantity = ml.quantity_product_uom
            picking.move_ids.picked = True
            picking.button_validate()
            self._update_in_move_lines()

    def action_open_close_wizard(self):
        """Open the close wizard to let the user decide qty_keep."""
        self.ensure_one()
        if self.state != "returned":
            raise UserError(_("Só é possível fechar sessões retornadas."))
        return {
            "type": "ir.actions.act_window",
            "name": "Fechamento de Sessão Van",
            "res_model": "van.session.close.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def action_post(self):
        """Generate closing account.move, state → closed."""
        for session in self:
            if session.state != "returned":
                raise UserError(_("Só é possível fechar sessões retornadas."))
            # Create unload picking if not yet created
            if not session.unload_picking_id:
                session._create_unload_picking()
            # Auto-validate unload picking if pending
            session._auto_validate_unload_picking()

            config = session.pos_config_id
            journal = config.van_journal_id
            if not journal:
                raise UserError(
                    _("Configure o diário de fechamento no POS %s.")
                    % config.display_name
                )

            lines_to_charge = session.line_ids.filtered(
                lambda ln: ln.amount > 0 and not ln.waived
            )
            total = sum(lines_to_charge.mapped("amount"))

            move_lines = []
            if total:
                # Debit driver account
                move_lines.append(
                    (
                        0,
                        0,
                        {
                            "account_id": config.van_driver_account_id.id,
                            "debit": total,
                            "credit": 0.0,
                            "name": "Diferença van %s" % session.name,
                        },
                    )
                )
                # Credit transit account
                move_lines.append(
                    (
                        0,
                        0,
                        {
                            "account_id": config.van_transit_account_id.id,
                            "debit": 0.0,
                            "credit": total,
                            "name": "Diferença van %s" % session.name,
                        },
                    )
                )

            if session.cash_diff:
                abs_diff = abs(session.cash_diff)
                if session.cash_diff < 0:
                    # Missing cash: debit driver, credit cash
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "account_id": config.van_driver_account_id.id,
                                "debit": abs_diff,
                                "credit": 0.0,
                                "name": "Diferença caixa %s" % session.name,
                            },
                        )
                    )
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "account_id": config.van_cash_account_id.id,
                                "debit": 0.0,
                                "credit": abs_diff,
                                "name": "Diferença caixa %s" % session.name,
                            },
                        )
                    )
                else:
                    # Excess cash: debit cash, credit driver
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "account_id": config.van_cash_account_id.id,
                                "debit": abs_diff,
                                "credit": 0.0,
                                "name": "Diferença caixa %s" % session.name,
                            },
                        )
                    )
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "account_id": config.van_driver_account_id.id,
                                "debit": 0.0,
                                "credit": abs_diff,
                                "name": "Diferença caixa %s" % session.name,
                            },
                        )
                    )

            if not move_lines:
                session.date_close = fields.Date.context_today(self)
                session.state = "closed"
                continue

            move = self.env["account.move"].create(
                {
                    "journal_id": journal.id,
                    "date": session.date,
                    "ref": session.name,
                    "line_ids": move_lines,
                }
            )
            move.action_post()
            session.move_id = move
            session.date_close = fields.Date.context_today(self)
            session.state = "closed"


class VanSessionLine(models.Model):
    _name = "van.session.line"
    _description = "Van Session Line"

    session_id = fields.Many2one(
        "van.session", required=True, ondelete="cascade", index=True
    )
    product_id = fields.Many2one("product.product", required=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            pricelist = self.session_id.pricelist_id
            if pricelist:
                self.price_unit = pricelist._get_product_price(
                    self.product_id, self.qty_out or 1.0
                )
            else:
                self.price_unit = self.product_id.lst_price

    out_move_line_ids = fields.Many2many(
        "stock.move.line",
        "van_line_out_sml_rel",
        "van_line_id",
        "sml_id",
        string="Out Move Lines",
    )
    sale_move_line_ids = fields.Many2many(
        "stock.move.line",
        "van_line_sale_sml_rel",
        "van_line_id",
        "sml_id",
        string="Sale Move Lines",
    )
    in_move_line_ids = fields.Many2many(
        "stock.move.line",
        "van_line_in_sml_rel",
        "van_line_id",
        "sml_id",
        string="In Move Lines",
    )
    qty_initial = fields.Float(
        string="Estoque Inicial",
        help="Quantidade já presente no caminhão antes da carga.",
    )
    qty_out = fields.Float(string="Qty Saída")
    qty_sold = fields.Float(
        string="Qty Vendida", compute="_compute_qty_sold", store=True
    )
    qty_returned = fields.Float(
        string="Qty Retornada", compute="_compute_qty_returned", store=True
    )
    qty_diff = fields.Float(string="Diferença", compute="_compute_qty_diff", store=True)
    qty_keep = fields.Float(
        string="Manter no Caminhão",
        help="Quantidade a manter no caminhão para a próxima sessão.",
    )
    price_unit = fields.Float(string="Preço Unitário")
    amount = fields.Float(
        string="Valor Diferença", compute="_compute_amount", store=True
    )
    waived = fields.Boolean()
    waive_reason = fields.Char(string="Motivo Abono")

    def copy_data(self, default=None):
        default = dict(default or {})
        default.update(
            {
                "out_move_line_ids": [(5, 0, 0)],
                "sale_move_line_ids": [(5, 0, 0)],
                "in_move_line_ids": [(5, 0, 0)],
                "qty_initial": 0,
                "qty_keep": 0,
                "waived": False,
                "waive_reason": False,
            }
        )
        return super().copy_data(default=default)

    @api.depends("sale_move_line_ids.quantity")
    def _compute_qty_sold(self):
        for line in self:
            line.qty_sold = sum(line.sale_move_line_ids.mapped("quantity"))

    @api.depends("in_move_line_ids.quantity")
    def _compute_qty_returned(self):
        for line in self:
            line.qty_returned = sum(line.in_move_line_ids.mapped("quantity"))

    @api.depends("qty_out", "qty_sold", "qty_returned", "qty_keep")
    def _compute_qty_diff(self):
        for line in self:
            line.qty_diff = (
                line.qty_out - line.qty_sold - line.qty_returned - line.qty_keep
            )

    @api.depends("qty_diff", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty_diff * line.price_unit

    @api.constrains("qty_keep", "qty_out", "qty_sold")
    def _check_qty_keep(self):
        for line in self:
            remaining = line.qty_out - line.qty_sold
            if line.qty_keep < 0:
                raise ValidationError(_("A quantidade a manter não pode ser negativa."))
            if line.qty_keep > remaining:
                raise ValidationError(
                    _(
                        "A quantidade a manter (%(qty_keep)s) não pode exceder"
                        " o saldo disponível (%(remaining)s) para o produto"
                        " %(product)s."
                    )
                    % {
                        "qty_keep": line.qty_keep,
                        "remaining": remaining,
                        "product": line.product_id.display_name,
                    }
                )

    @api.constrains("waived", "waive_reason")
    def _check_waive_reason(self):
        for line in self:
            if line.waived and (not line.waive_reason or len(line.waive_reason) < 20):
                raise ValidationError(
                    _("O motivo do abono deve ter pelo menos 20 caracteres.")
                )
