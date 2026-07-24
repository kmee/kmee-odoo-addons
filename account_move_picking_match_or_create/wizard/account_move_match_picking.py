from odoo import api, fields, models


class AccountMoveMatchPicking(models.TransientModel):
    _name = "account.move.match.picking"
    _description = "Match Pickings from Invoice"

    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Account Move",
    )
    state = fields.Selection(
        selection=[
            ("main", "Main"),
            ("select", "Select"),
        ],
        default="main",
    )
    stock_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Stock Pickings",
    )
    candidate_stock_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Candidate Stock Pickings",
        relation="match_picking_candidate_rel",
    )
    candidate_stock_picking_count = fields.Integer(
        string="Candidate Pickings Count",
    )
    candidate_match_line_ids = fields.One2many(
        comodel_name="account.move.match.picking.line",
        inverse_name="candidate_match_wizard_id",
        string="Candidate Match Lines",
    )
    new_match_line_ids = fields.One2many(
        comodel_name="account.move.match.picking.line",
        inverse_name="new_match_wizard_id",
        string="New Match Lines",
    )
    new_stock_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="New Stock Pickings",
        relation="match_picking_new_rel",
    )
    matching_invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Matching Lines",
        relation="match_picking_matching_lines_rel",
    )
    full_match_invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Full Match Lines",
        compute="_compute_match_status",
        relation="match_picking_full_match_rel",
    )
    partial_match_invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Partial Match Lines",
        compute="_compute_match_status",
        relation="match_picking_partial_rel",
    )
    unmatched_invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Unmatched Lines",
        compute="_compute_match_status",
        relation="match_picking_unmatched_rel",
    )
    count_lines = fields.Integer(
        string="Total Lines",
        compute="_compute_match_status",
    )
    count_lines_matched = fields.Integer(
        string="Matched Lines",
        compute="_compute_match_status",
    )
    count_lines_matching = fields.Integer(
        string="Matching Lines Count",
    )
    matching_progress = fields.Float(
        string="Progress",
        compute="_compute_match_status",
    )
    can_action_exact_match = fields.Boolean(
        string="Can Exact Match",
        compute="_compute_can_actions",
    )
    can_action_create_all = fields.Boolean(
        string="Can Create All",
        compute="_compute_can_actions",
    )
    can_action_match_create = fields.Boolean(
        string="Can Match and Create",
        compute="_compute_can_actions",
    )

    @api.depends("matching_invoice_line_ids", "account_move_id")
    def _compute_match_status(self):
        for wizard in self:
            move = wizard.account_move_id
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.display_type == "product"
            )
            matched = wizard.matching_invoice_line_ids
            wizard.count_lines = len(product_lines)
            wizard.count_lines_matched = len(matched)
            wizard.full_match_invoice_line_ids = matched
            wizard.partial_match_invoice_line_ids = self.env["account.move.line"]
            wizard.unmatched_invoice_line_ids = product_lines - matched
            if wizard.count_lines:
                wizard.matching_progress = (
                    wizard.count_lines_matched / wizard.count_lines * 100
                )
            else:
                wizard.matching_progress = 0

    @api.depends("candidate_match_line_ids", "unmatched_invoice_line_ids")
    def _compute_can_actions(self):
        for wizard in self:
            wizard.can_action_exact_match = bool(wizard.candidate_match_line_ids)
            wizard.can_action_create_all = bool(wizard.unmatched_invoice_line_ids)
            wizard.can_action_match_create = (
                wizard.can_action_exact_match or wizard.can_action_create_all
            )

    def _compute_candidate_pickings(self):
        for wizard in self:
            move = wizard.account_move_id
            partner = move.partner_id
            domain = [
                ("partner_id", "=", partner.id),
                ("state", "in", ["assigned", "done"]),
            ]
            if move.move_type in ("out_invoice", "out_refund"):
                domain.append(("picking_type_code", "=", "outgoing"))
            else:
                domain.append(("picking_type_code", "=", "incoming"))
            pickings = self.env["stock.picking"].search(domain)
            already_linked = (
                move.picking_ids
                if hasattr(move, "picking_ids")
                else self.env["stock.picking"]
            )
            candidates = pickings - already_linked
            wizard.candidate_stock_picking_ids = candidates
            wizard.candidate_stock_picking_count = len(candidates)
            lines = []
            for picking in candidates:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "picking_id": picking.id,
                            "candidate_match_wizard_id": wizard.id,
                        },
                    )
                )
            wizard.candidate_match_line_ids = lines

    def action_exact_match(self):
        self.ensure_one()
        move = self.account_move_id
        for line in self.candidate_match_line_ids:
            picking = line.picking_id
            for move_line in move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.display_type == "product"
            ):
                for stock_move in picking.move_ids:
                    if stock_move.product_id == move_line.product_id:
                        self.matching_invoice_line_ids |= move_line
                        self.stock_picking_ids |= picking
                        break
        return self._reopen()

    def action_create_all(self):
        self.ensure_one()
        move = self.account_move_id
        picking_type = self.env["stock.picking.type"].search(
            [
                ("company_id", "=", move.company_id.id),
                (
                    "code",
                    "=",
                    "outgoing"
                    if move.move_type in ("out_invoice", "out_refund")
                    else "incoming",
                ),
            ],
            limit=1,
        )
        if not picking_type:
            return self._reopen()
        picking_vals = {
            "partner_id": move.partner_id.id,
            "picking_type_id": picking_type.id,
            "origin": move.name,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "move_ids": [],
        }
        for line in self.unmatched_invoice_line_ids:
            if not line.product_id:
                continue
            picking_vals["move_ids"].append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.quantity,
                        "product_uom": line.product_uom_id.id,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": picking_type.default_location_dest_id.id,
                    },
                )
            )
        if picking_vals["move_ids"]:
            picking = self.env["stock.picking"].create(picking_vals)
            self.new_stock_picking_ids |= picking
            self.matching_invoice_line_ids |= self.unmatched_invoice_line_ids
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Match or Create Pickings",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class AccountMoveMatchPickingLine(models.TransientModel):
    _name = "account.move.match.picking.line"
    _description = "Match Picking Line"

    candidate_match_wizard_id = fields.Many2one(
        comodel_name="account.move.match.picking",
        string="Candidate Match Wizard",
    )
    new_match_wizard_id = fields.Many2one(
        comodel_name="account.move.match.picking",
        string="New Match Wizard",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Transfer",
        required=True,
    )
    partner_id = fields.Many2one(
        related="picking_id.partner_id",
    )
    origin = fields.Char(
        related="picking_id.origin",
    )
    state = fields.Selection(
        related="picking_id.state",
    )
    priority = fields.Selection(
        related="picking_id.priority",
    )
    scheduled_date = fields.Datetime(
        related="picking_id.scheduled_date",
    )
    has_unreserved = fields.Boolean()
    p_line_match = fields.Float(string="Matching Lines")
    p_qty_match = fields.Float(string="Approx. Qty. Match")
