# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import BaseCase, tagged

from ..utils import bpmn_xml as bx
from .common import (
    add_flow,
    add_task_after,
    change_lane,
    edit,
    move,
    remove_element,
    rename,
    sample_xml,
    set_doc,
)


@tagged("post_install", "-at_install")
class TestBpmnXml(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = sample_xml()

    def _names(self, xml):
        return {e["bpmn_id"]: e for e in bx.read_model(xml)["elements"]}

    def test_read_model(self):
        model = bx.read_model(self.base)
        elements = {e["bpmn_id"]: e for e in model["elements"]}
        self.assertEqual(len(elements), 6)
        quote = elements["Task_Sample_Quote"]
        self.assertEqual(quote["odoo"], "res.partner / Contacts")
        self.assertEqual(quote["sdd"], "2.1 Quotation")
        self.assertEqual(quote["requirements"], "SAL-01, SAL-02")
        self.assertEqual(quote["status"], "decided")
        self.assertEqual(quote["lane"], "Lane_Sample_Sales")
        invoice = elements["Task_Sample_Invoice"]
        self.assertEqual(invoice["status"], "proposal")
        self.assertEqual(invoice["sdd"], "3.4 Invoicing")
        self.assertEqual(invoice["lane"], "Lane_Sample_Billing")
        self.assertEqual(len(model["lanes"]), 2)

    def test_parse_documentation(self):
        info = bx.parse_documentation(
            "odoo: fora do sistema (planilha)\nsdd: 5.2\nrequisitos: -\n"
            "status: em aberto\nobservacao livre"
        )
        self.assertEqual(info["odoo"], "fora do sistema (planilha)")
        self.assertEqual(info["requirements"], "")
        self.assertEqual(info["status"], "open")
        self.assertEqual(info["notes"], "observacao livre")
        self.assertEqual(bx.parse_documentation("status: xyz")["notes"], "status: xyz")
        text = bx.format_documentation("a / b", "1.1", "R1", "proposal")
        again = bx.parse_documentation(text)
        self.assertEqual(again["status"], "proposal")
        self.assertEqual(again["requirements"], "R1")

    def test_invalid_document(self):
        with self.assertRaises(bx.BpmnError):
            bx.parse_tree("<root/>")
        with self.assertRaises(bx.BpmnError):
            bx.parse_tree("not xml")

    def test_diff(self):
        self.assertTrue(bx.diff_is_empty(bx.diff(self.base, self.base)))
        new = edit(self.base, rename("Task_Sample_Quote", "Send quote"))
        new = edit(new, move("Task_Sample_Invoice", dx=40))
        new = edit(
            new,
            add_task_after(
                "Task_Sample_Quote", "Task_New", "Check", "Lane_Sample_Sales"
            ),
        )
        new = edit(new, remove_element("End_Sample_Lost"))
        result = bx.diff(self.base, new)
        self.assertIn("Task_New", result["added"])
        self.assertIn("End_Sample_Lost", result["removed"])
        self.assertIn("attrs", result["changed"]["Task_Sample_Quote"])
        self.assertIn("Task_Sample_Invoice", result["moved"])
        self.assertEqual(result["names"]["Task_New"], "Check")

    def test_merge_independent_changes(self):
        ours = edit(self.base, move("Task_Sample_Invoice", dy=10))
        ours = edit(ours, set_doc("Task_Sample_Invoice", "status: decidido"))
        theirs = edit(self.base, rename("Task_Sample_Quote", "Send quote"))
        theirs = edit(
            theirs,
            add_task_after(
                "Task_Sample_Quote", "Task_New", "Check", "Lane_Sample_Billing"
            ),
        )
        merged, conflicts, problems = bx.merge(self.base, ours, theirs)
        self.assertFalse(conflicts)
        self.assertFalse(problems)
        elements = self._names(merged)
        self.assertEqual(elements["Task_Sample_Quote"]["name"], "Send quote")
        self.assertEqual(elements["Task_Sample_Invoice"]["status"], "decided")
        self.assertEqual(elements["Task_New"]["lane"], "Lane_Sample_Billing")
        self.assertEqual(elements["Task_New"]["bounds"]["x"], 300)
        self.assertEqual(elements["Task_Sample_Invoice"]["bounds"]["y"], 355)
        self.assertFalse(bx.validate(merged))
        # incoming/outgoing are rebuilt from the flows
        self.assertIn(
            "<bpmn:incoming>Flow_Sample_Quote_Approved</bpmn:incoming>", merged
        )
        self.assertIn("<bpmn:outgoing>Flow_Task_New_out</bpmn:outgoing>", merged)

    def test_merge_conflict_and_resolution(self):
        ours = edit(self.base, rename("Task_Sample_Quote", "Ours"))
        theirs = edit(self.base, rename("Task_Sample_Quote", "Theirs"))
        merged, conflicts, problems = bx.merge(self.base, ours, theirs)
        self.assertIsNone(merged)
        self.assertEqual([c.key() for c in conflicts], ["Task_Sample_Quote:attrs"])
        self.assertIn("Theirs", conflicts[0].as_dict()["theirs"])
        merged, conflicts, problems = bx.merge(
            self.base, ours, theirs, resolutions={"Task_Sample_Quote:attrs": "theirs"}
        )
        self.assertEqual(self._names(merged)["Task_Sample_Quote"]["name"], "Theirs")
        merged, conflicts, problems = bx.merge(
            self.base, ours, theirs, resolutions={"Task_Sample_Quote:attrs": "ours"}
        )
        self.assertEqual(self._names(merged)["Task_Sample_Quote"]["name"], "Ours")

    def test_merge_remove_against_change(self):
        ours = edit(self.base, set_doc("End_Sample_Lost", "status: em aberto"))
        theirs = edit(self.base, remove_element("End_Sample_Lost"))
        merged, conflicts, problems = bx.merge(self.base, ours, theirs)
        self.assertEqual([c.key() for c in conflicts], ["End_Sample_Lost:element"])
        # Untouched in ours: the removal goes through.
        merged, conflicts, problems = bx.merge(self.base, self.base, theirs)
        self.assertFalse(conflicts)
        self.assertNotIn("End_Sample_Lost", self._names(merged))

    def test_merge_structure_validation(self):
        ours = edit(
            self.base, add_flow("Flow_Extra", "Task_Sample_Quote", "End_Sample_Lost")
        )
        theirs = edit(self.base, remove_element("End_Sample_Lost"))
        merged, conflicts, problems = bx.merge(self.base, ours, theirs)
        self.assertIsNone(merged)
        self.assertFalse(conflicts)
        self.assertTrue(any("Flow_Extra" in p for p in problems))

    def test_merge_lane_and_position_preference(self):
        theirs = edit(
            self.base, change_lane("Task_Sample_Quote", "Lane_Sample_Billing")
        )
        theirs = edit(theirs, move("Task_Sample_Quote", dy=150))
        ours = edit(self.base, move("Task_Sample_Quote", dx=20))
        merged, conflicts, problems = bx.merge(self.base, ours, theirs)
        quote = self._names(merged)["Task_Sample_Quote"]
        self.assertEqual(quote["lane"], "Lane_Sample_Billing")
        self.assertEqual(quote["bounds"]["x"], 290)  # ours wins by default
        merged, conflicts, problems = bx.merge(
            self.base, ours, theirs, di_prefer="theirs"
        )
        self.assertEqual(self._names(merged)["Task_Sample_Quote"]["bounds"]["y"], 345)

    def test_apply_element_state(self):
        xml = bx.apply_element_state(
            self.base,
            {
                "Task_Sample_Invoice": {
                    "documentation": bx.format_documentation(sdd="3.4", status="open"),
                    "status": "open",
                }
            },
        )
        invoice = self._names(xml)["Task_Sample_Invoice"]
        self.assertEqual(invoice["status"], "open")
        self.assertIn('color:background-color="#ffebee"', xml)
