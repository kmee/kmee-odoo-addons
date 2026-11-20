# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakeRfqRound(models.TransientModel):
    _name = "purchase.request.line.make.rfq.round"
    _description = "Create Quotation Round from Purchase Request Lines"

    request_line_ids = fields.Many2many("purchase.request.line", readonly=True)
    round_id = fields.Many2one(
        "purchase.rfq.round",
        string="Add to Round",
        domain="[('state', '=', 'draft')]",
        help="Deixe vazio para criar uma rodada nova.",
    )
    vendor_ids = fields.Many2many(
        "res.partner",
        string="Vendors",
        help="Deixe vazio para sugerir os fornecedores cadastrados nos produtos.",
    )
    date_deadline = fields.Date(string="Answer Deadline")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "purchase.request.line":
            lines = self.env["purchase.request.line"].browse(
                self.env.context.get("active_ids", [])
            )
            self._check_request_lines(lines)
            res["request_line_ids"] = [Command.set(lines.ids)]
        return res

    @api.model
    def _check_request_lines(self, lines):
        if not lines:
            raise UserError(_("Select the purchase request lines to quote."))
        not_approved = lines.filtered(
            lambda line: line.request_state not in ("approved", "in_progress")
        )
        if not_approved:
            raise UserError(
                _(
                    "Only approved requests can be quoted: %s",
                    ", ".join(not_approved.mapped("request_id.name")),
                )
            )
        in_round = lines.filtered("rfq_round_id")
        if in_round:
            raise UserError(
                _(
                    "Some lines are already in an open quotation round: %s",
                    ", ".join(in_round.mapped("rfq_round_id.name")),
                )
            )

    def action_create(self):
        self.ensure_one()
        self._check_request_lines(self.request_line_ids)
        rfq_round = self.round_id or self.env["purchase.rfq.round"].create(
            {"date_deadline": self.date_deadline}
        )
        rfq_round.add_request_lines(self.request_line_ids)
        if self.vendor_ids:
            rfq_round.vendor_ids = [Command.link(v.id) for v in self.vendor_ids]
        else:
            rfq_round.action_suggest_vendors()
        return rfq_round._get_form_action()
