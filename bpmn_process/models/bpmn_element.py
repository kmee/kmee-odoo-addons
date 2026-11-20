# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models

from ..utils import bpmn_xml

STATUS = [("decided", "Decided"), ("proposal", "Proposal"), ("open", "Open")]
TEST_STATE = [("none", "No test"), ("passed", "Passed"), ("failed", "Failed")]


class BpmnElement(models.Model):
    _name = "bpmn.element"
    _description = "BPMN Element"
    _inherit = ["mail.thread"]
    _mail_post_access = "read"
    _order = "process_id, sequence, id"

    process_id = fields.Many2one(
        "bpmn.process", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="process_id.company_id", store=True)
    bpmn_id = fields.Char(string="BPMN Id", required=True, readonly=True, index=True)
    name = fields.Char()
    element_type = fields.Char(string="Type", readonly=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    lane_id = fields.Many2one(
        "bpmn.lane",
        domain="[('process_id', '=', process_id)]",
        tracking=True,
    )
    status = fields.Selection(STATUS, tracking=True)
    sdd_ref = fields.Char(string="Design reference", tracking=True)
    requirement_refs = fields.Char(string="Requirements", tracking=True)
    notes = fields.Text()
    odoo_ref = fields.Char(
        string="Odoo reference",
        help="The 'odoo:' line of the BPMN documentation, as imported.",
    )
    outside_system = fields.Boolean(
        help="The task is done outside Odoo (the 'odoo:' line says so)."
    )
    model_id = fields.Many2one(
        "ir.model", string="Odoo model", ondelete="set null", tracking=True
    )
    menu_id = fields.Many2one(
        "ir.ui.menu", string="Odoo menu", ondelete="set null", tracking=True
    )
    action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Odoo action",
        ondelete="set null",
        tracking=True,
    )
    manual_link = fields.Boolean(
        help="The Odoo model, menu or action was set by hand: imports keep it."
    )
    version_in_id = fields.Many2one(
        "bpmn.process.version", string="Added in", readonly=True
    )
    version_out_id = fields.Many2one(
        "bpmn.process.version", string="Removed in", readonly=True
    )
    test_ids = fields.One2many("bpmn.element.test", "element_id", string="Tests")
    test_state = fields.Selection(TEST_STATE, compute="_compute_test_state")
    is_mine = fields.Boolean(compute="_compute_is_mine")

    _sql_constraints = [
        (
            "bpmn_id_process_uniq",
            "unique(process_id, bpmn_id)",
            "An element id must be unique within the process.",
        )
    ]

    @api.depends("test_ids.result", "test_ids.date", "test_ids.scenario")
    def _compute_test_state(self):
        for element in self:
            latest = {}
            for test in element.test_ids.sorted(lambda t: (t.date, t.id)):
                latest[test.scenario] = test.result
            results = set(latest.values())
            if "failed" in results:
                element.test_state = "failed"
            elif "passed" in results:
                element.test_state = "passed"
            else:
                element.test_state = "none"

    @api.depends("lane_id.group_ids")
    @api.depends_context("uid")
    def _compute_is_mine(self):
        groups = self.env.user.groups_id
        for element in self:
            element.is_mine = bool(element.lane_id.group_ids & groups)

    def write(self, vals):
        if not self.env.context.get("bpmn_import") and {
            "model_id",
            "menu_id",
            "action_id",
        } & set(vals):
            vals = dict(vals, manual_link=True)
        return super().write(vals)

    # ------------------------------------------------------------------
    # Link with Odoo
    # ------------------------------------------------------------------

    def _resolve_odoo_link(self, odoo_ref, action_ref=""):
        """Model, menu and action named by the documentation lines.

        ``odoo_ref`` is ``<model> / <menu>`` (or 'fora do sistema (...)');
        ``action_ref`` is an optional XML id of a window action. Ambiguous
        menus are left empty for a person to fill in.
        """
        vals = {
            "model_id": False,
            "menu_id": False,
            "action_id": False,
            "outside_system": False,
        }
        text = (odoo_ref or "").strip()
        low = text.lower()
        if low.startswith(("fora do sistema", "outside", "manual")):
            vals["outside_system"] = True
            return vals
        if action_ref:
            action = self.env.ref(action_ref.strip(), raise_if_not_found=False)
            if action and action._name == "ir.actions.act_window":
                vals["action_id"] = action.id
        if not text or text == "-":
            return vals
        model_name, __, menu_name = (p.strip() for p in text.partition("/"))
        model = self.env["ir.model"]._get(model_name) if model_name else None
        if model:
            vals["model_id"] = model.id
        menu = self._find_menu(menu_name, model_name if model else "")
        if menu:
            vals["menu_id"] = menu.id
            if not vals["action_id"] and menu.action._name == "ir.actions.act_window":
                vals["action_id"] = menu.action.id
        return vals

    def _find_menu(self, menu_name, model_name):
        Menu = self.env["ir.ui.menu"].sudo()
        menus = Menu.browse()
        if menu_name:
            menus = Menu.search([("name", "=ilike", menu_name)])
            if len(menus) > 1 and model_name:
                menus = menus.filtered(
                    lambda m: m.action
                    and m.action._name == "ir.actions.act_window"
                    and m.action.res_model == model_name
                )
        elif model_name:
            actions = (
                self.env["ir.actions.act_window"]
                .sudo()
                .search([("res_model", "=", model_name)])
            )
            menus = Menu.search(
                [
                    (
                        "action",
                        "in",
                        ["ir.actions.act_window,%d" % a.id for a in actions],
                    )
                ]
            )
        return menus if len(menus) == 1 else Menu.browse()

    def _open_action(self):
        """What the 'Open in Odoo' button runs, for the viewer."""
        self.ensure_one()
        link = self.sudo()
        if link.action_id:
            return link.action_id.id
        if link.model_id:
            return {
                "type": "ir.actions.act_window",
                "name": link.model_id.name,
                "res_model": link.model_id.model,
                "views": [[False, "list"], [False, "form"]],
                "target": "current",
            }
        return False

    def action_open_odoo(self):
        self.ensure_one()
        action = self._open_action()
        if isinstance(action, int):
            return self.env["ir.actions.act_window"].browse(action)._get_action_dict()
        return action

    def action_show_in_diagram(self):
        self.ensure_one()
        return self.process_id.action_open_viewer(element=self.bpmn_id)

    # ------------------------------------------------------------------
    # Documentation
    # ------------------------------------------------------------------

    def _documentation(self):
        self.ensure_one()
        link = self.sudo()
        if self.outside_system:
            odoo = self.odoo_ref or _("outside the system")
        elif link.model_id:
            odoo = link.model_id.model
            if link.menu_id:
                odoo = "%s / %s" % (odoo, link.menu_id.name)
        else:
            odoo = self.odoo_ref or ""
        return bpmn_xml.format_documentation(
            odoo=odoo,
            sdd=self.sdd_ref,
            requirements=self.requirement_refs,
            status=self.status,
            notes=self.notes,
        )

    # ------------------------------------------------------------------
    # Viewer panel
    # ------------------------------------------------------------------

    def get_panel_data(self):
        self.ensure_one()
        messages = self.env["mail.message"].search(
            [
                ("model", "=", self._name),
                ("res_id", "=", self.id),
                ("message_type", "in", ["comment", "notification"]),
            ],
            limit=30,
        )
        status_labels = dict(self._fields["status"]._description_selection(self.env))
        # Labels of the link only: reading ir.model needs no extra right.
        link = self.sudo()
        result_labels = dict(
            self.env["bpmn.element.test"]
            ._fields["result"]
            ._description_selection(self.env)
        )
        return {
            "id": self.id,
            "bpmn_id": self.bpmn_id,
            "name": self.name or self.bpmn_id,
            "element_type": self.element_type,
            "lane": self.lane_id.name or "",
            "status": self.status or "",
            "status_label": status_labels.get(self.status, ""),
            "sdd_ref": self.sdd_ref or "",
            "requirement_refs": self.requirement_refs or "",
            "notes": self.notes or "",
            "odoo_ref": self.odoo_ref or "",
            "outside_system": self.outside_system,
            "odoo_label": link.action_id.name
            or link.menu_id.complete_name
            or link.model_id.name
            or "",
            "open_action": self._open_action(),
            "test_state": self.test_state,
            "tests": [
                {
                    "scenario": t.scenario,
                    "result": t.result,
                    "result_label": result_labels.get(t.result, ""),
                    "environment": t.environment or "",
                    "date": fields.Datetime.to_string(t.date),
                    "evidence_url": t.evidence_url or "",
                }
                for t in self.test_ids[:20]
            ],
            "messages": [
                {
                    "id": m.id,
                    "author": m.author_id.name or "",
                    "date": fields.Datetime.to_string(m.date),
                    "body": m.body or "",
                    "tracking": [
                        {
                            "field": v["changedField"],
                            "old": v["oldValue"]["value"] or "",
                            "new": v["newValue"]["value"] or "",
                        }
                        for v in m.sudo().tracking_value_ids._tracking_value_format()
                    ],
                }
                for m in messages
            ],
        }

    def post_comment(self, body):
        """Post a comment from the diagram panel (plain text)."""
        self.ensure_one()
        body = (body or "").strip()
        if not body:
            return False
        message = self.message_post(
            body=body, message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        self.process_id._notify_change("comment", element=self.bpmn_id)
        return message.id
