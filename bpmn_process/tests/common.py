# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import os

from lxml import etree

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"


def sample_xml():
    path = os.path.join(os.path.dirname(__file__), "data", "sample.bpmn")
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def edit(xml, func):
    """Apply ``func(root)`` to a parsed copy of ``xml`` and serialize it."""
    root = etree.fromstring(xml.encode("utf-8"))
    func(root)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


def by_id(root, eid):
    for el in root.iter():
        if isinstance(el.tag, str) and el.get("id") == eid:
            return el
    raise KeyError(eid)


def rename(eid, name):
    def _apply(root):
        by_id(root, eid).set("name", name)

    return _apply


def move(eid, dx=0, dy=0):
    def _apply(root):
        for shape in root.iter("{%s}BPMNShape" % DI_NS):
            if shape.get("bpmnElement") == eid:
                bounds = shape.find("{%s}Bounds" % DC_NS)
                bounds.set("x", str(float(bounds.get("x")) + dx))
                bounds.set("y", str(float(bounds.get("y")) + dy))

    return _apply


def set_doc(eid, text):
    def _apply(root):
        el = by_id(root, eid)
        for doc in el.findall("{%s}documentation" % BPMN_NS):
            el.remove(doc)
        doc = etree.Element("{%s}documentation" % BPMN_NS)
        doc.text = text
        el.insert(0, doc)

    return _apply


def remove_element(eid):
    """Remove an element, its flows, lane refs and diagram shapes."""

    def _apply(root):
        flows = [
            f.get("id")
            for f in root.iter("{%s}sequenceFlow" % BPMN_NS)
            if eid in (f.get("sourceRef"), f.get("targetRef"))
        ]
        doomed = set(flows) | {eid}
        for el in list(root.iter()):
            if not isinstance(el.tag, str):
                continue
            if el.get("id") in doomed or el.get("bpmnElement") in doomed:
                el.getparent().remove(el)
            elif (
                el.tag
                in (
                    "{%s}flowNodeRef" % BPMN_NS,
                    "{%s}incoming" % BPMN_NS,
                    "{%s}outgoing" % BPMN_NS,
                )
                and (el.text or "").strip() in doomed
            ):
                el.getparent().remove(el)

    return _apply


def add_task_after(source_id, new_id, name, lane_id):
    """Insert a user task between ``source_id`` and its first successor."""

    def _apply(root):
        process = by_id(root, source_id).getparent()
        flow = next(
            f
            for f in process.findall("{%s}sequenceFlow" % BPMN_NS)
            if f.get("sourceRef") == source_id
        )
        old_target = flow.get("targetRef")
        flow.set("targetRef", new_id)
        task = etree.SubElement(process, "{%s}userTask" % BPMN_NS)
        task.set("id", new_id)
        task.set("name", name)
        new_flow = etree.SubElement(process, "{%s}sequenceFlow" % BPMN_NS)
        new_flow.set("id", "Flow_%s_out" % new_id)
        new_flow.set("sourceRef", new_id)
        new_flow.set("targetRef", old_target)
        ref = etree.SubElement(by_id(root, lane_id), "{%s}flowNodeRef" % BPMN_NS)
        ref.text = new_id
        plane = next(root.iter("{%s}BPMNPlane" % DI_NS))
        shape = etree.SubElement(plane, "{%s}BPMNShape" % DI_NS)
        shape.set("id", new_id + "_di")
        shape.set("bpmnElement", new_id)
        bounds = etree.SubElement(shape, "{%s}Bounds" % DC_NS)
        for key, value in (
            ("x", "300"),
            ("y", "330"),
            ("width", "120"),
            ("height", "80"),
        ):
            bounds.set(key, value)
        edge = etree.SubElement(plane, "{%s}BPMNEdge" % DI_NS)
        edge.set("id", "Flow_%s_out_di" % new_id)
        edge.set("bpmnElement", "Flow_%s_out" % new_id)
        for x in ("420", "560"):
            point = etree.SubElement(edge, "{%s}waypoint" % DI_NS)
            point.set("x", x)
            point.set("y", "370")

    return _apply


def change_lane(eid, lane_id):
    def _apply(root):
        for ref in list(root.iter("{%s}flowNodeRef" % BPMN_NS)):
            if (ref.text or "").strip() == eid:
                ref.getparent().remove(ref)
        ref = etree.SubElement(by_id(root, lane_id), "{%s}flowNodeRef" % BPMN_NS)
        ref.text = eid

    return _apply


def add_flow(flow_id, source, target):
    def _apply(root):
        process = by_id(root, source).getparent()
        flow = etree.SubElement(process, "{%s}sequenceFlow" % BPMN_NS)
        flow.set("id", flow_id)
        flow.set("sourceRef", source)
        flow.set("targetRef", target)

    return _apply
