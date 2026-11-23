# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ORIGINS = [
    ("import", "Import"),
    ("edit", "Edit in Odoo"),
    ("restore", "Restore"),
    ("merge", "Merge"),
]


class BpmnProcessVersion(models.Model):
    """Immutable version of a diagram: the audit trail of the process."""

    _name = "bpmn.process.version"
    _description = "BPMN Process Version"
    _order = "process_id, number desc"

    process_id = fields.Many2one(
        "bpmn.process", required=True, ondelete="cascade", index=True, readonly=True
    )
    company_id = fields.Many2one(related="process_id.company_id", store=True)
    number = fields.Integer(required=True, readonly=True)
    xml = fields.Text(string="BPMN XML", required=True, readonly=True, prefetch=False)
    checksum = fields.Char(readonly=True, index=True)
    origin = fields.Selection(ORIGINS, required=True, readonly=True)
    parent_id = fields.Many2one(
        "bpmn.process.version", string="Based on", readonly=True
    )
    merge_parent_id = fields.Many2one(
        "bpmn.process.version",
        string="Merged with",
        readonly=True,
        help="For a merge: the incoming file merged into the version it is "
        "based on.",
    )
    note = fields.Text(readonly=True)
    diff_json = fields.Text(readonly=True, prefetch=False)
    diff_summary = fields.Text(string="Changes", readonly=True)
    is_current = fields.Boolean(compute="_compute_is_current")

    _sql_constraints = [
        (
            "number_process_uniq",
            "unique(process_id, number)",
            "Version numbers are unique within the process.",
        )
    ]

    @api.depends("process_id.current_version_id")
    def _compute_is_current(self):
        for version in self:
            version.is_current = version.process_id.current_version_id == version

    @api.depends("process_id.code", "number")
    def _compute_display_name(self):
        for version in self:
            version.display_name = "%s v%s" % (
                version.process_id.code or "",
                version.number,
            )

    def write(self, vals):  # pylint: disable=method-required-super
        raise UserError(_("A diagram version cannot be changed. Restore it instead."))

    def unlink(self):  # pylint: disable=method-required-super
        raise UserError(_("A diagram version cannot be deleted."))

    def get_diff(self):
        self.ensure_one()
        return json.loads(self.diff_json or "{}")

    def action_restore(self):
        self.ensure_one()
        self.process_id._check_manager()
        self.process_id._check_lock_free()
        version = self.process_id._create_version(
            self.xml,
            "restore",
            note=_("Restored from version %s.", self.number),
            parent=self.process_id.current_version_id,
        )
        if not version:
            raise UserError(_("This version is the same as the current one."))
        return self.process_id.action_open_viewer()

    def action_download(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/bpmn_process/version/%s" % self.id,
            "target": "download",
        }

    def action_view_diagram(self):
        self.ensure_one()
        return self.process_id.action_open_viewer(version=self)

    def action_compare_current(self):
        self.ensure_one()
        return self.process_id.action_open_viewer(
            version=self.process_id.current_version_id, compare=self
        )
