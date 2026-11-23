# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""BPMN 2.0 XML handling without Odoo: parse, semantic diff and three-way merge.

Every element is keyed by its BPMN id, which the generators keep stable. A
"tracked" element is a direct child of a process, sub-process, collaboration or
lane set (flow nodes, sequence and message flows, participants, artifacts,
lanes) or a root element of the definitions. Its comparable state is:

- ``attrs``: XML attributes except ``id``;
- ``documentation``: text of the ``bpmn:documentation`` children;
- ``body``: canonical XML of the remaining children, except the ones that are
  derived (``incoming``/``outgoing``), tracked on their own (nested flow
  elements, lanes) or represented by another property (``flowNodeRef``);
- ``lane``: id of the lane holding the element (flow nodes only);
- ``parent``: id of the semantic container.

The diagram interchange (BPMN DI) of an element is compared separately, so a
move is never a conflict.
"""

import copy
import hashlib
import json

from lxml import etree

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}
BPMN = "{%s}" % NS["bpmn"]
BPMNDI = "{%s}" % NS["bpmndi"]
COLOR_NS = "http://www.omg.org/spec/BPMN/non-normative/color/1.0"
BIOC_NS = "http://bpmn.io/schema/bpmn/biocolor/1.0"

CONTAINERS = {"process", "subProcess", "adHocSubProcess", "transaction"}
FLOW_NODES = {
    "task",
    "userTask",
    "serviceTask",
    "manualTask",
    "scriptTask",
    "sendTask",
    "receiveTask",
    "businessRuleTask",
    "callActivity",
    "subProcess",
    "adHocSubProcess",
    "transaction",
    "startEvent",
    "endEvent",
    "intermediateThrowEvent",
    "intermediateCatchEvent",
    "boundaryEvent",
    "exclusiveGateway",
    "inclusiveGateway",
    "parallelGateway",
    "eventBasedGateway",
    "complexGateway",
}
DERIVED_CHILDREN = {"incoming", "outgoing", "flowNodeRef", "childLaneSet"}
PROPS = ("attrs", "documentation", "body", "lane", "parent")

STATUS_WORDS = {
    "decided": (
        "decidido",
        "decidida",
        "combinado",
        "combinada",
        "certo",
        "confirmado",
        "aprovado",
        "decided",
        "agreed",
    ),
    "proposal": (
        "proposta",
        "proposta da kmee",
        "duvida",
        "dúvida",
        "a validar",
        "proposal",
    ),
    "open": ("em aberto", "aberto", "aberta", "pendente", "open", "pending"),
}
STATUS_COLORS = {
    "decided": ("#e8f5e9", "#2e7d32"),
    "proposal": ("#fff8e1", "#b7791f"),
    "open": ("#ffebee", "#c62828"),
}


class BpmnError(ValueError):
    """The XML is not a BPMN 2.0 document this module can handle."""


def local(tag):
    if not isinstance(tag, str):
        return ""
    return etree.QName(tag).localname


def parse_tree(xml):
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    if not xml or not xml.strip():
        raise BpmnError("Empty BPMN document.")
    parser = etree.XMLParser(
        remove_blank_text=False, resolve_entities=False, no_network=True
    )
    try:
        root = etree.fromstring(xml, parser)
    except etree.XMLSyntaxError as exc:
        raise BpmnError("Invalid XML: %s" % exc) from exc
    if root.tag != BPMN + "definitions":
        raise BpmnError("The root element must be bpmn:definitions.")
    return root


def to_string(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def checksum(xml):
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    return hashlib.sha256(xml).hexdigest()


def _canonical(node):
    node = copy.deepcopy(node)
    for el in node.iter():
        if el.text is not None and not el.text.strip():
            el.text = None
        if el.tail is not None and not el.tail.strip():
            el.tail = None
    return etree.tostring(node, method="c14n").decode("utf-8")


def _doc_text(el):
    return "\n".join(
        (d.text or "").strip() for d in el.findall(BPMN + "documentation")
    ).strip()


def _is_tracked_child(parent, child):
    if not isinstance(child.tag, str) or not child.get("id"):
        return False
    pname = local(parent.tag)
    if parent.tag == BPMN + "definitions":
        return child.tag.startswith(BPMN)
    if pname in CONTAINERS or pname in ("collaboration", "laneSet"):
        return child.tag.startswith(BPMN) and local(child.tag) != "documentation"
    if pname == "lane":
        return False
    return False


def _body(el, tracked_ids):
    parts = []
    for child in el:
        if not isinstance(child.tag, str):
            continue
        name = local(child.tag)
        if child.tag.startswith(BPMN) and (
            name in DERIVED_CHILDREN or name == "documentation"
        ):
            continue
        if child.get("id") in tracked_ids:
            continue
        if name == "laneSet":
            continue
        parts.append(_canonical(child))
    return "".join(parts)


def _semantic_parent(el):
    parent = el.getparent()
    while parent is not None and local(parent.tag) in ("laneSet", "lane"):
        parent = parent.getparent()
    if parent is None or parent.tag == BPMN + "definitions":
        return ""
    return parent.get("id") or ""


def _lane_of(root):
    lanes = {}
    for lane in root.iter(BPMN + "lane"):
        for ref in lane.findall(BPMN + "flowNodeRef"):
            # The innermost lane wins (iter is document order, children last).
            lanes[(ref.text or "").strip()] = lane.get("id")
    return lanes


def _tracked_nodes(root):
    nodes = {}

    def walk(parent):
        for child in parent:
            if _is_tracked_child(parent, child):
                nodes[child.get("id")] = child
            if isinstance(child.tag, str) and child.tag.startswith(BPMN):
                walk(child)

    walk(root)
    return nodes


def _di_index(root):
    index = {}
    for el in root.iter(BPMNDI + "BPMNShape", BPMNDI + "BPMNEdge"):
        ref = el.get("bpmnElement")
        if ref:
            index[ref] = el
    return index


def _di_state(el):
    node = copy.deepcopy(el)
    node.attrib.pop("id", None)
    return _canonical(node)


def _bounds(di):
    if di is None:
        return None
    b = di.find("{%s}Bounds" % NS["dc"])
    if b is None:
        return None
    try:
        return {k: float(b.get(k, 0)) for k in ("x", "y", "width", "height")}
    except ValueError:
        return None


def snapshot(root):
    """Comparable state of every tracked element and of its DI."""
    nodes = _tracked_nodes(root)
    tracked_ids = set(nodes)
    lanes = _lane_of(root)
    di = _di_index(root)
    elements = {}
    for eid, el in nodes.items():
        attrs = {k: v for k, v in el.attrib.items() if k != "id"}
        elements[eid] = {
            "tag": local(el.tag),
            "attrs": json.dumps(attrs, sort_keys=True),
            "documentation": _doc_text(el),
            "body": _body(el, tracked_ids),
            "lane": lanes.get(eid, "") if local(el.tag) in FLOW_NODES else "",
            "parent": _semantic_parent(el),
        }
    di_state = {ref: _di_state(el) for ref, el in di.items()}
    return {"elements": elements, "di": di_state}


# ---------------------------------------------------------------------------
# Reading for the Odoo records
# ---------------------------------------------------------------------------


def normalize_status(value):
    if not value:
        return False
    text = value.strip().lower().rstrip(".")
    for status, words in STATUS_WORDS.items():
        if text in words:
            return status
    for status, words in STATUS_WORDS.items():
        if any(text.startswith(w) for w in words):
            return status
    return False


def parse_documentation(text):
    """Read the documentation convention of the element.

    Fixed lines ``odoo:``, ``sdd:``, ``requisitos:`` (or ``requirements:``),
    ``status:`` and the optional ``acao:`` (or ``action:``); also the one-line
    form ``Status: combinado. SDD: 6.2 V2``. Unknown lines go to ``notes``.
    """
    result = {
        "odoo": "",
        "sdd": "",
        "requirements": "",
        "status": False,
        "action": "",
        "notes": "",
    }
    if not text:
        return result
    keys = {
        "odoo": "odoo",
        "sdd": "sdd",
        "requisitos": "requirements",
        "requirements": "requirements",
        "status": "status",
        "acao": "action",
        "ação": "action",
        "action": "action",
    }
    notes = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("status:") and ". sdd:" in low:
            idx = low.index(". sdd:")
            result["status"] = normalize_status(line[len("status:") : idx])
            result["sdd"] = line[idx + len(". sdd:") :].strip()
            continue
        key, sep, value = line.partition(":")
        field = keys.get(key.strip().lower()) if sep else None
        if not field:
            notes.append(line)
            continue
        value = value.strip()
        if field == "status":
            result["status"] = normalize_status(value)
            if not result["status"]:
                notes.append(line)
        elif field == "requirements":
            result["requirements"] = "" if value == "-" else value
        else:
            result[field] = value
    result["notes"] = "\n".join(notes)
    return result


def format_documentation(odoo="", sdd="", requirements="", status=False, notes=""):
    labels = {
        "decided": "decidido",
        "proposal": "proposta",
        "open": "em aberto",
    }
    lines = [
        "odoo: %s" % (odoo or "-"),
        "sdd: %s" % (sdd or "-"),
        "requisitos: %s" % (requirements or "-"),
        "status: %s" % labels.get(status, "-"),
    ]
    if notes:
        lines.append(notes)
    return "\n".join(lines)


def read_model(xml):
    """Elements and lanes of the document, as plain dicts for the ORM."""
    root = parse_tree(xml)
    nodes = _tracked_nodes(root)
    lanes_by_node = _lane_of(root)
    di = _di_index(root)
    elements = []
    order = 0
    for eid, el in nodes.items():
        tag = local(el.tag)
        if tag not in FLOW_NODES:
            continue
        order += 1
        doc = _doc_text(el)
        info = parse_documentation(doc)
        elements.append(
            {
                "bpmn_id": eid,
                "element_type": tag,
                "name": (el.get("name") or "").strip(),
                "lane": lanes_by_node.get(eid, ""),
                "documentation": doc,
                "bounds": _bounds(di.get(eid)),
                "sequence": order,
                **info,
            }
        )
    lanes = []
    for lane in root.iter(BPMN + "lane"):
        lanes.append(
            {
                "bpmn_id": lane.get("id"),
                "name": (lane.get("name") or lane.get("id") or "").strip(),
                "members": [
                    (r.text or "").strip() for r in lane.findall(BPMN + "flowNodeRef")
                ],
            }
        )
    processes = [
        {"bpmn_id": p.get("id"), "name": p.get("name") or ""}
        for p in root.findall(BPMN + "process")
    ]
    return {"elements": elements, "lanes": lanes, "processes": processes}


# ---------------------------------------------------------------------------
# Semantic diff
# ---------------------------------------------------------------------------


def diff(old_xml, new_xml):
    """What changed from ``old_xml`` to ``new_xml``, by BPMN id."""
    old = snapshot(parse_tree(old_xml)) if old_xml else {"elements": {}, "di": {}}
    new = snapshot(parse_tree(new_xml))
    o_el, n_el = old["elements"], new["elements"]
    added = sorted(set(n_el) - set(o_el))
    removed = sorted(set(o_el) - set(n_el))
    changed = {}
    moved = []
    for eid in sorted(set(o_el) & set(n_el)):
        props = [p for p in PROPS + ("tag",) if o_el[eid].get(p) != n_el[eid].get(p)]
        if props:
            changed[eid] = props
        elif old["di"].get(eid) != new["di"].get(eid):
            moved.append(eid)
    touched = set(added) | set(removed) | set(moved) | set(changed)
    names, tags = {}, {}
    for snap_el in (n_el, o_el):
        for eid in touched & set(snap_el):
            attrs = json.loads(snap_el[eid]["attrs"])
            names.setdefault(eid, attrs.get("name") or eid)
            tags.setdefault(eid, snap_el[eid]["tag"])
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "moved": moved,
        "names": names,
        "tags": tags,
    }


def diff_is_empty(result):
    return not (
        result["added"] or result["removed"] or result["changed"] or result["moved"]
    )


# ---------------------------------------------------------------------------
# Three-way merge
# ---------------------------------------------------------------------------


class MergeConflict:
    __slots__ = ("bpmn_id", "prop", "base", "ours", "theirs", "name")

    def __init__(self, bpmn_id, prop, base, ours, theirs, name=""):
        self.bpmn_id = bpmn_id
        self.prop = prop
        self.base = base
        self.ours = ours
        self.theirs = theirs
        self.name = name

    def key(self):
        return "%s:%s" % (self.bpmn_id, self.prop)

    def as_dict(self):
        return {
            "key": self.key(),
            "bpmn_id": self.bpmn_id,
            "prop": self.prop,
            "name": self.name,
            "base": _display(self.prop, self.base),
            "ours": _display(self.prop, self.ours),
            "theirs": _display(self.prop, self.theirs),
        }


def _display(prop, state):
    if state is None:
        return "(removed)"
    if isinstance(state, dict):
        value = state.get(prop) if prop != "element" else state.get("attrs")
    else:
        value = state
    if prop in ("attrs", "element") and value:
        try:
            attrs = json.loads(value)
        except (TypeError, ValueError):
            return value
        return ", ".join("%s=%s" % (local(k), v) for k, v in sorted(attrs.items()))
    return value or ""


def _find_by_id(root, eid):
    for el in root.iter():
        if isinstance(el.tag, str) and el.get("id") == eid:
            return el
    return None


def _remove_element(root, eid):
    el = _find_by_id(root, eid)
    if el is not None and el.getparent() is not None:
        el.getparent().remove(el)
    for ref in list(root.iter(BPMN + "flowNodeRef")):
        if (ref.text or "").strip() == eid:
            ref.getparent().remove(ref)
    for dio in list(root.iter(BPMNDI + "BPMNShape", BPMNDI + "BPMNEdge")):
        if dio.get("bpmnElement") == eid:
            dio.getparent().remove(dio)


def _replace_children(target, source, tracked_ids):
    """Copy documentation and body of ``source`` into ``target``."""
    keep = []
    for child in list(target):
        name = local(child.tag) if isinstance(child.tag, str) else ""
        if (
            child.get("id") in tracked_ids
            or name in DERIVED_CHILDREN
            or name == "laneSet"
        ) and isinstance(child.tag, str):
            keep.append(child)
        target.remove(child)
    new_children = []
    for child in source:
        if not isinstance(child.tag, str):
            continue
        name = local(child.tag)
        if child.get("id") in tracked_ids or name in DERIVED_CHILDREN:
            continue
        if name == "laneSet":
            continue
        new_children.append(copy.deepcopy(child))
    docs = [c for c in new_children if local(c.tag) == "documentation"]
    ext = [c for c in new_children if local(c.tag) == "extensionElements"]
    rest = [c for c in new_children if c not in docs and c not in ext]
    for child in docs + ext + keep + rest:
        target.append(child)


def _set_attrs(target, attrs_json):
    attrs = json.loads(attrs_json)
    eid = target.get("id")
    target.attrib.clear()
    target.set("id", eid)
    for k, v in attrs.items():
        target.set(k, v)


def _set_documentation(target, text):
    for d in target.findall(BPMN + "documentation"):
        target.remove(d)
    if text:
        doc = etree.Element(BPMN + "documentation")
        doc.text = text
        target.insert(0, doc)


def _set_lane(root, eid, lane_id):
    for ref in list(root.iter(BPMN + "flowNodeRef")):
        if (ref.text or "").strip() == eid:
            ref.getparent().remove(ref)
    if lane_id:
        lane = _find_by_id(root, lane_id)
        if lane is not None:
            ref = etree.SubElement(lane, BPMN + "flowNodeRef")
            ref.text = eid
            child_set = lane.find(BPMN + "childLaneSet")
            if child_set is not None:
                lane.remove(child_set)
                lane.append(child_set)


def _set_di(root, eid, theirs_root):
    source = _di_index(theirs_root).get(eid)
    ours = _di_index(root).get(eid)
    if source is None:
        if ours is not None:
            ours.getparent().remove(ours)
        return
    new = copy.deepcopy(source)
    if ours is not None:
        ours.getparent().replace(ours, new)
        return
    plane = _plane_for(root, theirs_root, source)
    if plane is not None:
        plane.append(new)


def _plane_for(root, other_root, other_di):
    other_plane = other_di.getparent()
    plane_ref = other_plane.get("bpmnElement") if other_plane is not None else None
    for plane in root.iter(BPMNDI + "BPMNPlane"):
        if plane.get("bpmnElement") == plane_ref:
            return plane
    return next(root.iter(BPMNDI + "BPMNPlane"), None)


def _insert_new(root, theirs_root, eid, state):
    source = _find_by_id(theirs_root, eid)
    parent_id = state["parent"]
    if parent_id:
        parent = _find_by_id(root, parent_id)
    else:
        parent = root
    if parent is None:
        return False
    new = copy.deepcopy(source)
    # Nested tracked elements are handled one by one; drop them here.
    for child in list(new):
        if (
            isinstance(child.tag, str)
            and child.get("id")
            and (
                local(child.tag) in FLOW_NODES
                or local(child.tag) in ("sequenceFlow", "laneSet")
            )
        ):
            new.remove(child)
    if parent is root:
        diagram = root.find(BPMNDI + "BPMNDiagram")
        if diagram is not None:
            diagram.addprevious(new)
        else:
            root.append(new)
    elif local(source.tag) == "lane":
        lane_set = parent.find(BPMN + "laneSet")
        if lane_set is None:
            lane_set = etree.SubElement(parent, BPMN + "laneSet")
            lane_set.set("id", "LaneSet_%s" % parent_id)
        lane_set.append(new)
    else:
        parent.append(new)
    return True


def _rebuild_flow_refs(root):
    """Regenerate incoming/outgoing of every flow node from the flows."""
    for container in root.iter():
        if not isinstance(container.tag, str) or local(container.tag) not in CONTAINERS:
            continue
        incoming, outgoing = {}, {}
        for flow in container.findall(BPMN + "sequenceFlow"):
            outgoing.setdefault(flow.get("sourceRef"), []).append(flow.get("id"))
            incoming.setdefault(flow.get("targetRef"), []).append(flow.get("id"))
        for node in container:
            if not isinstance(node.tag, str) or local(node.tag) not in FLOW_NODES:
                continue
            nid = node.get("id")
            for child in node.findall(BPMN + "incoming") + node.findall(
                BPMN + "outgoing"
            ):
                node.remove(child)
            pos = 0
            for i, child in enumerate(node):
                if isinstance(child.tag, str) and local(child.tag) in (
                    "documentation",
                    "extensionElements",
                ):
                    pos = i + 1
            refs = [("incoming", f) for f in incoming.get(nid, [])] + [
                ("outgoing", f) for f in outgoing.get(nid, [])
            ]
            for offset, (kind, fid) in enumerate(refs):
                ref = etree.Element(BPMN + kind)
                ref.text = fid
                node.insert(pos + offset, ref)


def validate(xml_or_root):
    """Structural problems that must block saving a merged or edited diagram."""
    root = (
        parse_tree(xml_or_root)
        if not isinstance(xml_or_root, etree._Element)
        else xml_or_root
    )
    problems = []
    ids = {
        el.get("id") for el in root.iter() if isinstance(el.tag, str) and el.get("id")
    }
    for flow in root.iter(BPMN + "sequenceFlow", BPMN + "messageFlow"):
        for attr in ("sourceRef", "targetRef"):
            ref = flow.get(attr)
            if not ref or ref not in ids:
                problems.append(
                    "Flow %s points to a missing %s (%s)."
                    % (flow.get("id"), attr, ref or "-")
                )
    for process in root.iter(BPMN + "process"):
        lane_set = process.find(BPMN + "laneSet")
        if lane_set is None:
            continue
        in_lane = {(r.text or "").strip() for r in lane_set.iter(BPMN + "flowNodeRef")}
        for node in process:
            if (
                isinstance(node.tag, str)
                and local(node.tag) in FLOW_NODES
                and node.get("id") not in in_lane
            ):
                problems.append(
                    "Element %s (%s) is outside every lane."
                    % (node.get("id"), node.get("name") or local(node.tag))
                )
    for ref in root.iter(BPMN + "flowNodeRef"):
        if (ref.text or "").strip() not in ids:
            problems.append("Lane points to a missing element (%s)." % ref.text)
    for dio in root.iter(BPMNDI + "BPMNShape", BPMNDI + "BPMNEdge"):
        if dio.get("bpmnElement") not in ids:
            problems.append(
                "Diagram shape %s points to a missing element (%s)."
                % (dio.get("id"), dio.get("bpmnElement"))
            )
    return problems


class _Merge:
    """State of one three-way merge; see :func:`merge`."""

    def __init__(self, base_xml, ours_xml, theirs_xml, resolutions, di_prefer):
        self.resolutions = resolutions or {}
        self.di_prefer = di_prefer
        self.theirs_root = parse_tree(theirs_xml)
        ours_root = parse_tree(ours_xml)
        self.base = snapshot(parse_tree(base_xml))
        self.ours = snapshot(ours_root)
        self.theirs = snapshot(self.theirs_root)
        self.result = copy.deepcopy(ours_root)
        self.tracked_ids = set(self.ours["elements"]) | set(self.theirs["elements"])
        self.conflicts = []
        self.lane_changes = {}

    def _state(self, eid):
        for snap in (self.theirs, self.ours, self.base):
            if eid in snap["elements"]:
                return snap["elements"][eid]
        return None

    def name_of(self, eid):
        state = self._state(eid)
        return json.loads(state["attrs"]).get("name") or eid if state else eid

    def depth(self, eid):
        """Containers first, so that new parents exist before their content."""
        level, seen = 0, set()
        state = self._state(eid)
        while state and state["parent"] and state["parent"] not in seen:
            seen.add(state["parent"])
            level += 1
            state = self._state(state["parent"])
        return level

    def pick(self, eid, prop, base, ours, theirs):
        conflict = MergeConflict(eid, prop, base, ours, theirs, self.name_of(eid))
        choice = self.resolutions.get(conflict.key())
        if choice not in ("ours", "theirs"):
            self.conflicts.append(conflict)
        return choice

    def take_whole(self, eid, state, replace=False):
        """Bring the element of the file into the result."""
        if replace:
            _remove_element(self.result, eid)
        if _insert_new(self.result, self.theirs_root, eid, state):
            if state["lane"]:
                self.lane_changes[eid] = state["lane"]
            _set_di(self.result, eid, self.theirs_root)

    def merge_element(self, eid):
        b = self.base["elements"].get(eid)
        o = self.ours["elements"].get(eid)
        t = self.theirs["elements"].get(eid)
        if o == t:
            return
        if b is None:
            if o is None:
                self.take_whole(eid, t)
            elif t is not None and self.pick(eid, "element", None, o, t) == "theirs":
                self.take_whole(eid, t, replace=True)
        elif t is None:
            if o is not None and (
                o == b or self.pick(eid, "element", b, o, None) == "theirs"
            ):
                _remove_element(self.result, eid)
        elif o is None:
            if t != b and self.pick(eid, "element", b, None, t) == "theirs":
                self.take_whole(eid, t)
        else:
            self.merge_props(eid, b, o, t)

    def merge_props(self, eid, b, o, t):
        target = _find_by_id(self.result, eid)
        for prop in PROPS:
            if o[prop] == t[prop] or t[prop] == b[prop]:
                continue  # same on both sides, or only Odoo changed it
            take_theirs = o[prop] == b[prop] or (
                self.pick(eid, prop, b[prop], o[prop], t[prop]) == "theirs"
            )
            if take_theirs and target is not None:
                self.apply_prop(eid, target, prop, t)

    def apply_prop(self, eid, target, prop, t):
        if prop == "attrs":
            _set_attrs(target, t["attrs"])
        elif prop == "documentation":
            _set_documentation(target, t["documentation"])
        elif prop == "body":
            current_doc = _doc_text(target)
            _replace_children(
                target, _find_by_id(self.theirs_root, eid), self.tracked_ids
            )
            _set_documentation(target, current_doc)
        elif prop == "lane":
            self.lane_changes[eid] = t["lane"]
        elif prop == "parent":
            parent = (
                _find_by_id(self.result, t["parent"]) if t["parent"] else self.result
            )
            if parent is not None:
                target.getparent().remove(target)
                parent.append(target)

    def merge_di(self):
        """A side that did not move an element never wins over one that did."""
        b_di, o_di, t_di = self.base["di"], self.ours["di"], self.theirs["di"]
        result_ids = {
            el.get("id")
            for el in self.result.iter()
            if isinstance(el.tag, str) and el.get("id")
        }
        for eid in set(o_di) | set(t_di):
            if eid not in result_ids or o_di.get(eid) == t_di.get(eid):
                continue
            ours_moved = o_di.get(eid) != b_di.get(eid)
            theirs_moved = t_di.get(eid) != b_di.get(eid)
            if (
                eid in t_di
                and theirs_moved
                and (not ours_moved or self.di_prefer == "theirs")
            ):
                _set_di(self.result, eid, self.theirs_root)
        for dio in list(self.result.iter(BPMNDI + "BPMNShape", BPMNDI + "BPMNEdge")):
            if dio.get("bpmnElement") not in result_ids:
                dio.getparent().remove(dio)

    def run(self):
        all_ids = (
            set(self.base["elements"])
            | set(self.ours["elements"])
            | set(self.theirs["elements"])
        )
        for eid in sorted(all_ids, key=lambda e: (self.depth(e), e)):
            self.merge_element(eid)
        for eid, lane_id in self.lane_changes.items():
            _set_lane(self.result, eid, lane_id)
        self.merge_di()
        if self.conflicts:
            return None, self.conflicts, []
        _rebuild_flow_refs(self.result)
        problems = validate(self.result)
        if problems:
            return None, [], problems
        return to_string(self.result), [], []


def merge(base_xml, ours_xml, theirs_xml, resolutions=None, di_prefer="ours"):
    """Three-way merge of BPMN documents.

    ``ours`` is the version in Odoo, ``theirs`` the incoming file and ``base``
    the version both started from. ``resolutions`` maps a conflict key
    (``"<bpmn id>:<prop>"``) to ``"ours"`` or ``"theirs"``; ``di_prefer``
    decides the position of an element moved on both sides.

    Returns ``(xml or None, conflicts, problems)``: the merged document is
    returned only when every conflict is resolved and the structure is valid.
    """
    return _Merge(base_xml, ours_xml, theirs_xml, resolutions, di_prefer).run()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def apply_element_state(xml, states, color=True):
    """Rewrite documentation and colors from the Odoo records.

    ``states`` maps a BPMN id to ``{"documentation": str, "status": str}``.
    """
    root = parse_tree(xml)
    di = _di_index(root)
    for eid, state in states.items():
        el = _find_by_id(root, eid)
        if el is None:
            continue
        if "documentation" in state:
            _set_documentation(el, state["documentation"])
        if color and state.get("status") in STATUS_COLORS and eid in di:
            fill, stroke = STATUS_COLORS[state["status"]]
            shape = di[eid]
            shape.set("{%s}background-color" % COLOR_NS, fill)
            shape.set("{%s}border-color" % COLOR_NS, stroke)
            for attr in ("fill", "stroke"):
                shape.attrib.pop("{%s}%s" % (BIOC_NS, attr), None)
    _ensure_ns(root)
    return to_string(root)


def _ensure_ns(root):
    """Declare the color namespace on the root when an element uses it."""
    if COLOR_NS in root.nsmap.values():
        return root
    uses = any(
        any(k.startswith("{%s}" % COLOR_NS) for k in el.attrib)
        for el in root.iter(BPMNDI + "BPMNShape")
    )
    if not uses:
        return root
    etree.cleanup_namespaces(root, top_nsmap={"color": COLOR_NS})
    return root
