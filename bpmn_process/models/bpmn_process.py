# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..utils import bpmn_xml

LOCK_MINUTES = 120


class BpmnProcess(models.Model):
    _name = "bpmn.process"
    _description = "BPMN Process"
    _inherit = ["mail.thread"]
    _mail_post_access = "read"
    _order = "code, id"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        required=True,
        index=True,
        help="Stable key of the process, usually the file name without the "
        "extension. Imports with the same code create new versions.",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )
    active = fields.Boolean(default=True)
    description = fields.Text()
    source = fields.Selection(
        [("file", "File generated outside Odoo"), ("odoo", "Edited in Odoo")],
        default="file",
        required=True,
        tracking=True,
        help="Where the diagram is maintained. It becomes 'Edited in Odoo' on "
        "the first save in the editor; imports are then merged.",
    )
    version_ids = fields.One2many(
        "bpmn.process.version", "process_id", string="Versions"
    )
    current_version_id = fields.Many2one(
        "bpmn.process.version", string="Current version", readonly=True, copy=False
    )
    current_version_number = fields.Integer(
        related="current_version_id.number", string="Version"
    )
    element_ids = fields.One2many("bpmn.element", "process_id", string="Elements")
    lane_ids = fields.One2many("bpmn.lane", "process_id", string="Lanes")
    element_count = fields.Integer(compute="_compute_counts")
    decided_count = fields.Integer(compute="_compute_counts", string="Decided")
    proposal_count = fields.Integer(compute="_compute_counts", string="Proposals")
    open_count = fields.Integer(compute="_compute_counts", string="Open")
    version_count = fields.Integer(compute="_compute_counts", string="Versions #")
    lock_user_id = fields.Many2one("res.users", string="Edited by", readonly=True)
    lock_date = fields.Datetime(readonly=True)

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The process code must be unique per company.",
        )
    ]

    @api.depends("element_ids.status", "version_ids")
    def _compute_counts(self):
        for process in self:
            statuses = process.element_ids.mapped("status")
            process.element_count = len(process.element_ids)
            process.decided_count = statuses.count("decided")
            process.proposal_count = statuses.count("proposal")
            process.open_count = statuses.count("open")
            process.version_count = len(process.version_ids)

    def unlink(self):
        if self.version_ids:
            raise UserError(
                _("A process with versions keeps its history: archive it instead.")
            )
        return super().unlink()

    # ------------------------------------------------------------------
    # Permissions and lock
    # ------------------------------------------------------------------

    def _is_manager(self):
        return self.env.user.has_group("bpmn_process.group_bpmn_manager")

    def _check_manager(self):
        if not self._is_manager():
            raise AccessError(_("Only process managers can change diagrams."))

    def _lock_holder(self):
        self.ensure_one()
        if not self.lock_user_id or not self.lock_date:
            return self.env["res.users"]
        if self.lock_date < fields.Datetime.now() - timedelta(minutes=LOCK_MINUTES):
            return self.env["res.users"]
        return self.lock_user_id

    def _check_lock_free(self):
        for process in self:
            holder = process._lock_holder()
            if holder and holder != self.env.user:
                raise UserError(
                    _(
                        "%(process)s is being edited by %(user)s.",
                        process=process.display_name,
                        user=holder.name,
                    )
                )

    def acquire_edit_lock(self):
        """Take (or renew) the edit lock. One person edits at a time."""
        self.ensure_one()
        self._check_manager()
        holder = self._lock_holder()
        if holder and holder != self.env.user:
            return {"ok": False, "user": holder.name}
        renewing = holder == self.env.user
        self.sudo().write(
            {"lock_user_id": self.env.user.id, "lock_date": fields.Datetime.now()}
        )
        if not renewing:
            self._notify_change("lock", user_id=self.env.user.id)
        return {"ok": True, "user": self.env.user.name}

    def release_edit_lock(self, force=False):
        self.ensure_one()
        holder = self._lock_holder()
        if holder and holder != self.env.user:
            if not force:
                return False
            self._check_manager()
            self.message_post(
                body=_("Edit lock of %s broken.", holder.name),
                subtype_xmlid="mail.mt_note",
            )
        self.sudo().write({"lock_user_id": False, "lock_date": False})
        self._notify_change("unlock")
        return True

    def action_break_lock(self):
        for process in self:
            process.release_edit_lock(force=True)

    def _notify_change(self, kind, **payload):
        group = self.env.ref("bpmn_process.group_bpmn_user", raise_if_not_found=False)
        if not group:
            return
        for process in self:
            self.env["bus.bus"].sudo()._sendone(
                group,
                "bpmn_process/updated",
                dict(
                    payload,
                    process_id=process.id,
                    kind=kind,
                    user=self.env.user.name,
                ),
            )

    # ------------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------------

    def _parse(self, xml):
        try:
            return bpmn_xml.read_model(xml)
        except bpmn_xml.BpmnError as exc:
            raise UserError(_("Invalid BPMN file: %s", exc)) from exc

    def _describe_ids(self, ids, names, tags, label):
        shown = [
            label(e)
            for e in ids
            if tags.get(e) in bpmn_xml.FLOW_NODES or names.get(e, e) != e
        ]
        others = len(ids) - len(shown)
        if others:
            shown.append(_("%s connections or structure items", others))
        return ", ".join(shown)

    def _summary(self, diff, divergences=None, extra=None, first=False):
        """Text of the changes of a version, for people.

        Elements are listed by name; unnamed connections and the pool and
        lane structure are only counted, so the summary stays readable.
        """
        names = diff.get("names", {})
        tags = diff.get("tags", {})
        labels = {
            "attrs": _("attributes"),
            "documentation": _("documentation"),
            "body": _("content"),
            "lane": _("lane"),
            "parent": _("container"),
            "tag": _("type"),
            "element": _("element"),
        }

        def label(eid):
            name = names.get(eid) or eid
            return name if name == eid else "%s (%s)" % (name, eid)

        def describe(ids):
            return self._describe_ids(ids, names, tags, label)

        if first:
            nodes = [e for e in diff["added"] if tags.get(e) in bpmn_xml.FLOW_NODES]
            lanes = [e for e in diff["added"] if tags.get(e) == "lane"]
            return _(
                "First version: %(elements)s elements in %(lanes)s lanes.",
                elements=len(nodes),
                lanes=len(lanes),
            )
        lines = []
        if diff["added"]:
            lines.append(_("Added: %s", describe(diff["added"])))
        if diff["removed"]:
            lines.append(_("Removed: %s", describe(diff["removed"])))
        for eid, props in diff["changed"].items():
            lines.append(
                _(
                    "Changed %(element)s: %(props)s",
                    element=label(eid),
                    props=", ".join(labels.get(p, p) for p in props),
                )
            )
        if diff["moved"]:
            lines.append(_("Moved: %s", describe(diff["moved"])))
        for item in divergences or []:
            lines.append(
                _(
                    "Status kept in Odoo for %(element)s: file says %(file)s, "
                    "Odoo says %(odoo)s",
                    **item,
                )
            )
        lines.extend(extra or [])
        return "\n".join(lines) or _("No change in the diagram.")

    def _create_version(
        self,
        xml,
        origin,
        note="",
        parent=None,
        merge_parent=None,
        set_current=True,
        extra_summary=None,
    ):
        """Create an immutable version; when current, sync the elements.

        Returns the version, or an empty recordset when the XML is the same
        as the current version.
        """
        self.ensure_one()
        model = self._parse(xml)
        digest = bpmn_xml.checksum(xml)
        current = self.current_version_id
        Version = self.env["bpmn.process.version"]
        if set_current and current and current.checksum == digest:
            return Version
        reference = current if set_current else parent
        diff = bpmn_xml.diff(reference.xml if reference else None, xml)
        divergences = self._status_divergences(model) if set_current else []
        number = (
            max(
                self.with_context(active_test=False).version_ids.mapped("number") or [0]
            )
            + 1
        )
        version = Version.create(
            {
                "process_id": self.id,
                "number": number,
                "xml": xml,
                "checksum": digest,
                "origin": origin,
                "note": note or False,
                "parent_id": parent.id if parent else False,
                "merge_parent_id": merge_parent.id if merge_parent else False,
                "diff_json": json.dumps(diff),
                "diff_summary": self._summary(
                    diff, divergences, extra_summary, first=not reference
                ),
            }
        )
        if set_current:
            self.write({"current_version_id": version.id})
            changed_docs = {
                eid
                for eid, props in diff["changed"].items()
                if "documentation" in props
            }
            self._sync_elements(model, version, changed_docs)
            origin_label = dict(
                Version._fields["origin"]._description_selection(self.env)
            )[origin]
            heading = _(
                "Version %(number)s (%(origin)s)%(note)s",
                number=number,
                origin=origin_label,
                note=(": %s" % note) if note else "",
            )
            self.message_post(
                body=Markup("<p><b>%s</b><br/>%s</p>")
                % (heading, Markup("<br/>").join(version.diff_summary.split("\n"))),
                subtype_xmlid="mail.mt_note",
            )
            self._notify_change("version", version=number)
        return version

    def _status_divergences(self, model):
        existing = {
            e.bpmn_id: e for e in self.with_context(active_test=False).element_ids
        }
        labels = dict(
            self.env["bpmn.element"]._fields["status"]._description_selection(self.env)
        )
        result = []
        for item in model["elements"]:
            record = existing.get(item["bpmn_id"])
            if (
                record
                and record.status
                and item["status"]
                and item["status"] != record.status
            ):
                result.append(
                    {
                        "element": record.name or record.bpmn_id,
                        "file": labels[item["status"]],
                        "odoo": labels[record.status],
                    }
                )
        return result

    def _sync_elements(self, model, version, changed_docs=()):
        """Bring lanes and elements in line with the current version.

        Elements are keyed by the BPMN id, so comments, status and links
        survive new versions. Values read from the documentation (design
        reference, requirements, notes, Odoo reference) are taken for new
        elements and when the documentation changed in this version; the
        status is taken only when the element has none (after that, the
        status belongs to Odoo).
        """
        self.ensure_one()
        Lane = self.env["bpmn.lane"].with_context(active_test=False)
        Element = self.env["bpmn.element"].with_context(
            active_test=False, bpmn_import=True, mail_create_nolog=True
        )
        lanes = {
            lane.bpmn_id: lane for lane in Lane.search([("process_id", "=", self.id)])
        }
        seen = Lane.browse()
        for sequence, item in enumerate(model["lanes"], 1):
            vals = {"name": item["name"], "sequence": sequence, "active": True}
            lane = lanes.get(item["bpmn_id"])
            if lane:
                changes = {k: v for k, v in vals.items() if lane[k] != v}
                if changes:
                    lane.write(changes)
            else:
                lane = Lane.create(
                    dict(vals, process_id=self.id, bpmn_id=item["bpmn_id"])
                )
            seen |= lane
        (Lane.browse([lane.id for lane in lanes.values()]) - seen).filtered(
            "active"
        ).write({"active": False})
        lane_by_bpmn = {lane.bpmn_id: lane for lane in seen}

        elements = {
            e.bpmn_id: e for e in Element.search([("process_id", "=", self.id)])
        }
        seen_elements = Element.browse()
        for item in model["elements"]:
            record = elements.get(item["bpmn_id"])
            lane = lane_by_bpmn.get(item["lane"])
            base = {
                "name": item["name"],
                "element_type": item["element_type"],
                "sequence": item["sequence"],
                "lane_id": lane.id if lane else False,
                "active": True,
                "version_out_id": False,
            }
            doc_vals = {
                "sdd_ref": item["sdd"] or False,
                "requirement_refs": item["requirements"] or False,
                "notes": item["notes"] or False,
                "odoo_ref": item["odoo"] or False,
            }
            if not record:
                vals = dict(base, **doc_vals)
                vals.update(
                    process_id=self.id,
                    bpmn_id=item["bpmn_id"],
                    status=item["status"] or False,
                    version_in_id=version.id,
                )
                vals.update(Element._resolve_odoo_link(item["odoo"], item["action"]))
                record = Element.create(vals)
            else:
                vals = dict(base)
                if item["bpmn_id"] in changed_docs:
                    vals.update(doc_vals)
                    if not record.manual_link:
                        vals.update(
                            Element._resolve_odoo_link(item["odoo"], item["action"])
                        )
                if not record.status and item["status"]:
                    vals["status"] = item["status"]
                vals = {
                    key: value
                    for key, value in vals.items()
                    if _differs(record[key], value)
                }
                if vals:
                    record.write(vals)
            seen_elements |= record
        gone = Element.browse([e.id for e in elements.values()]) - seen_elements
        gone.filtered("active").write({"active": False, "version_out_id": version.id})

    @api.model
    def import_xml(
        self,
        code,
        xml,
        note="",
        name=None,
        base_version=None,
        resolutions=None,
        di_prefer="ours",
        company_id=None,
    ):
        """Import a BPMN file generated outside Odoo (for scripts and the wizard).

        The first import creates the process. Later imports become a new
        version when nothing changed in Odoo since the version the file is
        based on (``base_version``, a version number; by default the last
        imported file). Otherwise the file is merged three ways with the
        current version: conflicts are returned for a person to choose
        (``resolutions`` maps ``"<bpmn id>:<property>"`` to ``"ours"`` (Odoo)
        or ``"theirs"`` (file)). ``di_prefer`` decides the position of an
        element moved on both sides.

        Returns a dict with ``status`` in created, updated, merged,
        unchanged, conflict, invalid or locked.
        """
        if isinstance(xml, bytes):
            xml = xml.decode("utf-8")
        model = self._parse(xml)
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )
        process = self.with_context(active_test=False).search(
            [("code", "=", code), ("company_id", "in", [company.id, False])], limit=1
        )
        if process:
            process._check_manager()
        else:
            self._check_manager()
            default_name = name or (
                model["processes"][0]["name"] if model["processes"] else ""
            )
            process = self.create(
                {"code": code, "name": default_name or code, "company_id": company.id}
            )
        if name and process.name != name:
            process.name = name
        result = {"process_id": process.id, "conflicts": [], "problems": []}
        holder = process._lock_holder()
        if holder and holder != self.env.user:
            return dict(result, status="locked", user=holder.name)
        current = process.current_version_id
        if not current:
            version = process._create_version(xml, "import", note=note)
            return dict(result, status="created", version=version.number)
        digest = bpmn_xml.checksum(xml)
        versions = process.version_ids.sorted("number", reverse=True)
        if base_version:
            base = versions.filtered(lambda v: v.number == base_version)
            if not base:
                raise UserError(_("Version %s does not exist.", base_version))
        else:
            base = versions.filtered(lambda v: v.origin == "import")[:1] or current
        if digest in (current.checksum, base.checksum):
            return dict(result, status="unchanged", version=current.number)
        if base == current:
            version = process._create_version(xml, "import", note=note, parent=base)
            return dict(result, status="updated", version=version.number)
        merged, conflicts, problems = bpmn_xml.merge(
            base.xml, current.xml, xml, resolutions=resolutions, di_prefer=di_prefer
        )
        if conflicts:
            return dict(
                result,
                status="conflict",
                base_version=base.number,
                conflicts=[c.as_dict() for c in conflicts],
            )
        if problems:
            return dict(
                result, status="invalid", base_version=base.number, problems=problems
            )
        incoming = process._create_version(
            xml,
            "import",
            note=note or _("File as received, merged in the next version."),
            parent=base,
            set_current=False,
        )
        extra = []
        if resolutions:
            extra.append(
                _(
                    "Conflicts resolved: %s",
                    ", ".join("%s=%s" % item for item in sorted(resolutions.items())),
                )
            )
        version = process._create_version(
            merged,
            "merge",
            note=note,
            parent=current,
            merge_parent=incoming,
            extra_summary=extra,
        )
        return dict(
            result,
            status="merged",
            version=(version or current).number,
            incoming_version=incoming.number,
        )

    def save_edited_xml(self, xml, note=""):
        """Save the diagram drawn in the Odoo editor (requires the lock)."""
        self.ensure_one()
        self._check_manager()
        if self._lock_holder() != self.env.user:
            raise UserError(_("Take the edit lock before saving."))
        problems = bpmn_xml.validate(xml)
        if problems:
            raise UserError("\n".join(problems))
        version = self._create_version(
            xml, "edit", note=note, parent=self.current_version_id
        )
        if self.source != "odoo":
            self.source = "odoo"
        self.release_edit_lock()
        return {"version": (version or self.current_version_id).number}

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_xml(self):
        """Current diagram with documentation and colors from the records."""
        self.ensure_one()
        if not self.current_version_id:
            return ""
        states = {
            element.bpmn_id: {
                "documentation": element._documentation(),
                "status": element.status,
            }
            for element in self.element_ids
        }
        return bpmn_xml.apply_element_state(self.current_version_id.xml, states)

    def action_export(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/bpmn_process/export/%s" % self.id,
            "target": "download",
        }

    @api.model
    def export_by_code(self, code):
        process = self.search([("code", "=", code)], limit=1)
        if not process:
            raise UserError(_("No process with code %s.", code))
        return {
            "xml": process.export_xml(),
            "version": process.current_version_id.number,
        }

    # ------------------------------------------------------------------
    # Viewer
    # ------------------------------------------------------------------

    def action_open_viewer(self, version=None, compare=None, element=None):
        self.ensure_one()
        params = {"process_id": self.id}
        if version:
            params["version_id"] = version.id
        if compare:
            params["compare_version_id"] = compare.id
        if element:
            params["element"] = element
        return {
            "type": "ir.actions.client",
            "tag": "bpmn_process.viewer",
            "name": self.display_name,
            "params": params,
            "context": {"active_id": self.id, "active_model": self._name},
        }

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "bpmn.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_process_id": self.id,
                "default_code": self.code,
                "default_name": self.name,
            },
        }

    def get_viewer_data(self, version_id=None, compare_version_id=None):
        self.ensure_one()
        Version = self.env["bpmn.process.version"]
        version = Version.browse(version_id) if version_id else self.current_version_id
        if version and version.process_id != self:
            raise UserError(_("The version does not belong to this process."))
        groups = self.env.user.groups_id
        message_counts = {}
        if self.element_ids:
            rows = self.env["mail.message"]._read_group(
                [
                    ("model", "=", "bpmn.element"),
                    ("res_id", "in", self.element_ids.ids),
                    ("message_type", "=", "comment"),
                ],
                ["res_id"],
                ["__count"],
            )
            message_counts = dict(rows)
        elements = {}
        for element in self.element_ids:
            elements[element.bpmn_id] = {
                "id": element.id,
                "name": element.name or element.bpmn_id,
                "status": element.status or "",
                "test_state": element.test_state,
                "messages": message_counts.get(element.id, 0),
                "mine": bool(element.lane_id.group_ids & groups),
                "has_link": bool(element.action_id or element.model_id),
            }
        diff = None
        if compare_version_id:
            compare = Version.browse(compare_version_id)
            if compare.process_id != self:
                raise UserError(_("The version does not belong to this process."))
            diff = bpmn_xml.diff(compare.xml, version.xml)
            diff["from"] = compare.number
            diff["to"] = version.number
        holder = self._lock_holder()
        origins = dict(Version._fields["origin"]._description_selection(self.env))
        return {
            "process": {
                "id": self.id,
                "name": self.name,
                "code": self.code,
                "source": self.source,
            },
            "xml": version.xml if version else "",
            "version": {
                "id": version.id,
                "number": version.number,
                "is_current": version == self.current_version_id,
            }
            if version
            else False,
            "versions": [
                {
                    "id": v.id,
                    "number": v.number,
                    "origin": origins[v.origin],
                    "user": v.create_uid.name,
                    "date": fields.Datetime.to_string(v.create_date),
                    "current": v == self.current_version_id,
                }
                for v in self.version_ids.sorted("number", reverse=True)
            ],
            "elements": elements,
            "can_manage": self._is_manager(),
            "lock": {
                "user": holder.name or "",
                "mine": bool(holder) and holder == self.env.user,
            },
            "diff": diff,
            "has_my_lanes": any(lane.group_ids & groups for lane in self.lane_ids),
        }


def _differs(current, value):
    if isinstance(current, models.BaseModel):
        return current.id != (value or False)
    return (current or False) != (value or False)
