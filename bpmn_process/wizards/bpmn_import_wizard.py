# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BpmnImportWizard(models.TransientModel):
    _name = "bpmn.import.wizard"
    _description = "Import BPMN Diagram"

    process_id = fields.Many2one("bpmn.process", readonly=True)
    code = fields.Char(required=True)
    name = fields.Char()
    file = fields.Binary(string="BPMN file", required=True)
    filename = fields.Char()
    note = fields.Char()
    base_version = fields.Integer(
        help="Version the file was based on. Empty: the last imported file."
    )
    di_prefer = fields.Selection(
        [("ours", "Odoo"), ("theirs", "File")],
        string="Position when moved on both sides",
        default="ours",
        required=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("conflict", "Conflicts"), ("invalid", "Invalid")],
        default="draft",
        required=True,
    )
    problems = fields.Text(readonly=True)
    line_ids = fields.One2many("bpmn.import.wizard.line", "wizard_id")

    @api.onchange("filename")
    def _onchange_filename(self):
        if self.filename and not self.code:
            self.code = os.path.splitext(os.path.basename(self.filename))[0]

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "name": _("Import BPMN diagram"),
        }

    def action_import(self):
        self.ensure_one()
        xml = base64.b64decode(self.file or b"").decode("utf-8")
        resolutions = {line.key: line.choice for line in self.line_ids if line.choice}
        result = self.env["bpmn.process"].import_xml(
            self.code.strip(),
            xml,
            note=self.note or "",
            name=self.name or None,
            base_version=self.base_version or None,
            resolutions=resolutions or None,
            di_prefer=self.di_prefer,
        )
        status = result["status"]
        if status == "locked":
            raise UserError(
                _("The diagram is being edited by %s. Try again later.", result["user"])
            )
        if status == "conflict":
            self.line_ids.unlink()
            self.write(
                {
                    "state": "conflict",
                    "base_version": result["base_version"],
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "key": c["key"],
                                "element": "%s (%s)" % (c["name"], c["bpmn_id"]),
                                "prop": c["prop"],
                                "base_value": c["base"],
                                "odoo_value": c["ours"],
                                "file_value": c["theirs"],
                                "choice": resolutions.get(c["key"]),
                            },
                        )
                        for c in result["conflicts"]
                    ],
                }
            )
            return self._reopen()
        if status == "invalid":
            self.write({"state": "invalid", "problems": "\n".join(result["problems"])})
            return self._reopen()
        process = self.env["bpmn.process"].browse(result["process_id"])
        return process.action_open_viewer()


class BpmnImportWizardLine(models.TransientModel):
    _name = "bpmn.import.wizard.line"
    _description = "BPMN Merge Conflict"

    wizard_id = fields.Many2one("bpmn.import.wizard", required=True, ondelete="cascade")
    key = fields.Char(required=True)
    element = fields.Char(readonly=True)
    prop = fields.Char(string="Property", readonly=True)
    base_value = fields.Text(string="Before", readonly=True)
    odoo_value = fields.Text(string="In Odoo", readonly=True)
    file_value = fields.Text(string="In the file", readonly=True)
    choice = fields.Selection([("ours", "Keep Odoo"), ("theirs", "Take the file")])
