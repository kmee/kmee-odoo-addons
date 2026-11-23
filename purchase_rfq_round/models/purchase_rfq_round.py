# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRfqRound(models.Model):
    """Rodada de cotação.

    Agrupa os itens a cotar (vindos de requisições aprovadas) e os
    fornecedores convidados. Cria uma cotação (RFQ) por fornecedor, todas no
    mesmo grupo de Alternativas do core, para reaproveitar a tela de comparar
    e o aviso de confirmação. A rodada guarda o que o grupo não guarda:
    referência de preço, respostas originais, vencedor por item e saving.
    """

    _name = "purchase.rfq.round"
    _description = "Quotation Round"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        required=True, copy=False, readonly=True, default=lambda self: _("New")
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("quoting", "Quoting"),
            ("done", "Closed"),
            ("replaced", "Replaced by next round"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    user_id = fields.Many2one(
        "res.users",
        string="Buyer",
        default=lambda self: self.env.user,
        tracking=True,
    )
    date_deadline = fields.Date(
        string="Answer Deadline",
        tracking=True,
        help="Data limite para os fornecedores responderem.",
    )
    round_number = fields.Integer(string="Round", default=1, readonly=True)
    parent_id = fields.Many2one(
        "purchase.rfq.round",
        string="Previous Round",
        readonly=True,
        copy=False,
        index=True,
    )
    child_ids = fields.One2many("purchase.rfq.round", "parent_id", readonly=True)
    vendor_ids = fields.Many2many(
        "res.partner",
        string="Vendors",
        domain="[('is_company', '=', True)]",
    )
    line_ids = fields.One2many(
        "purchase.rfq.round.line", "round_id", string="Items", copy=True
    )
    order_ids = fields.One2many(
        "purchase.order", "rfq_round_id", string="Quotations", readonly=True
    )
    order_count = fields.Integer(compute="_compute_order_count")
    response_ids = fields.One2many(
        "purchase.rfq.round.response", "round_id", string="Responses", readonly=True
    )
    response_count = fields.Integer(compute="_compute_response_count")
    note = fields.Html()
    amount_reference = fields.Monetary(
        compute="_compute_amounts", string="Reference Amount"
    )
    amount_awarded = fields.Monetary(compute="_compute_amounts", string="Awarded")
    amount_saving = fields.Monetary(compute="_compute_amounts", string="Saving")
    saving_percent = fields.Float(compute="_compute_amounts", string="Saving (%)")
    awarded_line_count = fields.Integer(compute="_compute_amounts")
    has_unsent_orders = fields.Boolean(
        compute="_compute_has_unsent_orders",
        help="Há cotação da rodada ainda não enviada ao fornecedor.",
    )
    line_count = fields.Integer(compute="_compute_amounts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "purchase.rfq.round"
                ) or _("New")
        return super().create(vals_list)

    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    @api.depends("order_ids.state")
    def _compute_has_unsent_orders(self):
        for rec in self:
            rec.has_unsent_orders = rec.state == "quoting" and any(
                order.state == "draft" for order in rec.order_ids
            )

    def _compute_response_count(self):
        for rec in self:
            rec.response_count = len(rec.response_ids)

    @api.depends(
        "line_ids.amount_reference",
        "line_ids.amount_awarded",
        "line_ids.awarded_po_line_id",
    )
    def _compute_amounts(self):
        for rec in self:
            awarded = rec.line_ids.filtered("awarded_po_line_id")
            rec.line_count = len(rec.line_ids)
            rec.awarded_line_count = len(awarded)
            rec.amount_reference = sum(awarded.mapped("amount_reference"))
            rec.amount_awarded = sum(awarded.mapped("amount_awarded"))
            rec.amount_saving = rec.amount_reference - rec.amount_awarded
            rec.saving_percent = (
                rec.amount_saving / rec.amount_reference * 100.0
                if rec.amount_reference
                else 0.0
            )

    # ------------------------------------------------------------------
    # Montagem
    # ------------------------------------------------------------------

    def _prepare_lines_from_request_lines(self, request_lines):
        """Consolida as linhas de requisição por produto e unidade."""
        grouped = {}
        for req_line in request_lines:
            uom = req_line.product_uom_id or req_line.product_id.uom_po_id
            key = (req_line.product_id.id, uom.id)
            pending = req_line.product_qty - req_line._get_rfq_round_converted_qty()
            if pending <= 0.0:
                continue
            item = grouped.setdefault(
                key,
                {
                    "product_id": req_line.product_id.id,
                    "product_uom_id": uom.id,
                    "product_qty": 0.0,
                    "request_line_ids": [],
                },
            )
            item["product_qty"] += pending
            item["request_line_ids"].append(req_line.id)
        return [
            Command.create(
                dict(vals, request_line_ids=[Command.set(vals["request_line_ids"])])
            )
            for vals in grouped.values()
        ]

    def add_request_lines(self, request_lines):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Items can only be added to a draft round."))
        self.write({"line_ids": self._prepare_lines_from_request_lines(request_lines)})

    def action_suggest_vendors(self):
        """Sugere os fornecedores cadastrados nos produtos da rodada."""
        for rec in self:
            vendors = rec.line_ids._get_suggested_sellers().partner_id
            rec.vendor_ids = [Command.link(v.id) for v in vendors]

    # ------------------------------------------------------------------
    # Cotações
    # ------------------------------------------------------------------

    def _get_job_threshold(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("purchase_rfq_round.job_threshold", 2000)
        )

    def action_create_rfqs(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("The quotations were already created."))
            if not rec.line_ids:
                raise UserError(_("Add the items to quote first."))
            if not rec.vendor_ids:
                raise UserError(_("Choose the vendors to invite."))
            size = len(rec.line_ids) * len(rec.vendor_ids)
            use_job = size > rec._get_job_threshold()
            first_order = rec._create_rfq_for_vendor(rec.vendor_ids[0])
            for vendor in rec.vendor_ids[1:]:
                if use_job:
                    rec.with_delay(
                        description=_("%(round)s: quotation for %(vendor)s")
                        % {"round": rec.name, "vendor": vendor.display_name}
                    )._create_rfq_for_vendor(vendor, first_order.id)
                else:
                    rec._create_rfq_for_vendor(vendor, first_order.id)
            rec.state = "quoting"
            if use_job:
                rec.message_post(
                    body=_(
                        "%(count)s quotations queued for creation " "(%(size)s lines).",
                        count=len(rec.vendor_ids) - 1,
                        size=size,
                    )
                )
        return True

    def _prepare_rfq_vals(self, vendor):
        self.ensure_one()
        return {
            "partner_id": vendor.id,
            "company_id": self.company_id.id,
            "user_id": self.user_id.id,
            "rfq_round_id": self.id,
            "origin": self.name,
            "order_line": [
                Command.create(line._prepare_rfq_line_vals(vendor))
                for line in self.line_ids
            ],
        }

    def _create_rfq_for_vendor(self, vendor, origin_order_id=False):
        """Cria a cotação de um fornecedor, já no grupo de Alternativas."""
        self.ensure_one()
        order = (
            self.env["purchase.order"]
            .with_company(self.company_id)
            .create(self._prepare_rfq_vals(vendor))
        )
        if origin_order_id:
            origin = self.env["purchase.order"].browse(origin_order_id)
            group = origin.purchase_group_id
            if group:
                order.purchase_group_id = group
            else:
                self.env["purchase.order.group"].create(
                    {"order_ids": [Command.set((origin | order).ids)]}
                )
        return order

    # ------------------------------------------------------------------
    # Envio
    # ------------------------------------------------------------------

    def _get_rfq_mail_attachments(self, order):
        """Anexos do e-mail de cada cotação.

        Ponto de extensão: ``purchase_rfq_round_sheet`` anexa a planilha
        padrão de resposta.
        """
        return self.env["ir.attachment"]

    def action_send_rfqs(self):
        """Envia por e-mail cada cotação em rascunho da rodada."""
        template = self.env.ref(
            "purchase.email_template_edi_purchase", raise_if_not_found=False
        )
        for rec in self:
            if rec.state != "quoting":
                raise UserError(_("Create the quotations before sending them."))
            for order in rec.order_ids.filtered(lambda o: o.state == "draft"):
                attachments = rec._get_rfq_mail_attachments(order)
                if order.partner_id.email and template:
                    # Mesmo layout do envio manual do core: o fornecedor
                    # recebe o botão de acesso à cotação no portal.
                    order.message_post_with_source(
                        template,
                        email_layout_xmlid=(
                            "mail.mail_notification_layout_with_responsible_signature"
                        ),
                        subtype_xmlid="mail.mt_comment",
                        partner_ids=order.partner_id.ids,
                        attachment_ids=attachments.ids,
                    )
                else:
                    order.message_post(
                        body=_(
                            "Vendor without e-mail: send the quotation by "
                            "another channel."
                        ),
                        attachment_ids=attachments.ids,
                    )
                order.write({"state": "sent"})
        return True

    # ------------------------------------------------------------------
    # Respostas
    # ------------------------------------------------------------------

    def _prepare_response_snapshot(self, po_line):
        order = po_line.order_id
        delay = 0
        if po_line.date_planned and order.date_order:
            delay = max((po_line.date_planned - order.date_order).days, 0)
        return {
            "round_id": self.id,
            "round_line_id": po_line.rfq_round_line_id.id,
            "order_id": order.id,
            "order_line_id": po_line.id,
            "partner_id": order.partner_id.id,
            "product_id": po_line.product_id.id,
            "price_unit": po_line.price_unit,
            "delay": delay,
            "source": "manual",
        }

    def _snapshot_responses(self):
        """Guarda as respostas digitadas na cotação que ainda não têm registro.

        Chamado ao fechar a rodada e ao abrir a seguinte, para que o
        histórico de respostas exista mesmo sem importação de planilha.
        """
        vals_list = []
        for rec in self:
            recorded = rec.response_ids.order_line_id
            for po_line in rec.line_ids.quote_line_ids:
                if (
                    po_line.price_unit > 0.0
                    and po_line.order_id.state != "cancel"
                    and po_line not in recorded
                ):
                    vals_list.append(rec._prepare_response_snapshot(po_line))
        self.env["purchase.rfq.round.response"].create(vals_list)

    # ------------------------------------------------------------------
    # Adjudicação
    # ------------------------------------------------------------------

    def _check_can_award(self):
        for rec in self:
            if rec.state != "quoting":
                raise UserError(_("Only rounds in quotation can be awarded."))

    def action_open_award(self):
        self.ensure_one()
        self._check_can_award()
        return {
            "type": "ir.actions.act_window",
            "name": _("Award"),
            "res_model": "purchase.rfq.round.award",
            "view_mode": "form",
            "target": "new",
            "context": {"default_round_id": self.id},
        }

    def _award_lines(self, criterion, only_unawarded=False):
        self._check_can_award()
        lines = self.line_ids
        if only_unawarded:
            lines = lines.filtered(lambda line: not line.awarded_po_line_id)
        for line in lines:
            line._award(line._get_best_quote(criterion))

    def action_award_best_price(self):
        self._check_can_award()
        for line in self.line_ids:
            line._award(line._get_best_quote("price"))
        return True

    def action_award_best_date(self):
        self._check_can_award()
        for line in self.line_ids:
            line._award(line._get_best_quote("date"))
        return True

    def action_close(self):
        """Fecha a rodada.

        Idempotente: rodada já fechada não muda. Cancela as cotações sem item
        vencedor, tira das vencedoras as linhas não vencedoras e liga as
        requisições só às linhas vencedoras. As vencedoras continuam como
        cotação e seguem a aprovação normal do pedido.
        """
        for rec in self.filtered(lambda r: r.state == "quoting"):
            awarded = rec.line_ids.awarded_po_line_id
            if not awarded:
                raise UserError(_("Award at least one item before closing."))
            rec._snapshot_responses()
            for order in rec.order_ids.filtered(lambda o: o.state != "cancel"):
                winners = order.order_line & awarded
                if not winners:
                    order.button_cancel()
                    continue
                losers = order.order_line.filtered(
                    lambda pol, w=winners: pol.product_id and pol not in w
                )
                losers.unlink()
            for line in rec.line_ids.filtered("awarded_po_line_id"):
                line._link_request_lines()
            rec.state = "done"
            rec.message_post(
                body=_(
                    "Round closed: %(awarded)s of %(total)s items awarded, "
                    "saving %(saving)s.",
                    awarded=rec.awarded_line_count,
                    total=rec.line_count,
                    saving=rec.currency_id.format(rec.amount_saving),
                )
            )
        return True

    def action_new_round(self):
        """Abre a rodada seguinte com o melhor preço desta como referência."""
        self.ensure_one()
        if self.state != "quoting":
            raise UserError(_("Only a round in quotation can be followed."))
        self._snapshot_responses()
        new_lines = []
        for line in self.line_ids:
            best = line._get_best_quote("price")
            reference = best.price_unit if best else line.reference_price
            new_lines.append(
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "product_uom_id": line.product_uom_id.id,
                        "product_qty": line.product_qty,
                        "request_line_ids": [Command.set(line.request_line_ids.ids)],
                        "reference_price": reference,
                        "reference_source": "previous_round",
                    }
                )
            )
        responded = self.order_ids.filtered(
            lambda o: any(o.order_line.mapped("price_unit"))
        ).partner_id
        new_round = self.copy(
            {
                "parent_id": self.id,
                "round_number": self.round_number + 1,
                "line_ids": new_lines,
                "vendor_ids": [Command.set((responded or self.vendor_ids).ids)],
                "date_deadline": False,
            }
        )
        self.order_ids.filtered(lambda o: o.state in ("draft", "sent")).button_cancel()
        self.state = "replaced"
        return new_round._get_form_action()

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("A closed round cannot be cancelled."))
            rec.order_ids.filtered(
                lambda o: o.state in ("draft", "sent", "to approve")
            ).button_cancel()
            rec.state = "cancel"
        return True

    def action_draft(self):
        for rec in self.filtered(lambda r: r.state == "cancel"):
            if rec.order_ids.filtered(lambda o: o.state != "cancel"):
                raise UserError(_("Cancel the quotations of the round first."))
            rec.state = "draft"
        return True

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _get_form_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.rfq.round",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        action["domain"] = [("rfq_round_id", "=", self.id)]
        action["context"] = {"default_rfq_round_id": self.id}
        return action

    def action_view_responses(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_rfq_round.purchase_rfq_round_response_action"
        )
        action["domain"] = [("round_id", "=", self.id)]
        return action

    def action_compare(self):
        """Matriz das cotações da rodada: linhas por item e fornecedor."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_rfq_round.purchase_rfq_round_quote_action"
        )
        action["domain"] = [
            ("rfq_round_line_id.round_id", "=", self.id),
            ("order_id.state", "!=", "cancel"),
        ]
        action["display_name"] = _("Compare %s", self.name)
        return action
