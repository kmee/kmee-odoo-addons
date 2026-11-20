# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..utils import bpmn_xml as bx
from .common import (
    add_task_after,
    edit,
    move,
    remove_element,
    rename,
    sample_xml,
    set_doc,
)


@tagged("post_install", "-at_install")
class TestBpmnProcess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=False))
        cls.xml = sample_xml()
        cls.manager = new_test_user(
            cls.env,
            login="bpmn_manager",
            groups="base.group_user,bpmn_process.group_bpmn_manager",
        )
        cls.manager2 = new_test_user(
            cls.env,
            login="bpmn_manager2",
            groups="base.group_user,bpmn_process.group_bpmn_manager",
        )
        cls.user = new_test_user(
            cls.env,
            login="bpmn_user",
            groups="base.group_user,bpmn_process.group_bpmn_user",
        )
        cls.Process = cls.env["bpmn.process"].with_user(cls.manager)

    def _import(self, xml, **kwargs):
        return self.Process.import_xml("sample", xml, **kwargs)

    def _process(self):
        return self.env["bpmn.process"].search([("code", "=", "sample")])

    def _element(self, bpmn_id):
        return (
            self.env["bpmn.element"]
            .with_context(active_test=False)
            .search([("bpmn_id", "=", bpmn_id), ("process_id.code", "=", "sample")])
        )

    def test_first_import(self):
        result = self._import(self.xml, note="first")
        self.assertEqual(result["status"], "created")
        process = self._process()
        self.assertEqual(process.name, "Sample sales")
        self.assertEqual(process.current_version_id.number, 1)
        self.assertEqual(process.element_count, 6)
        self.assertEqual(len(process.lane_ids), 2)
        self.assertEqual((process.decided_count, process.proposal_count), (1, 1))
        quote = self._element("Task_Sample_Quote")
        self.assertEqual(quote.status, "decided")
        self.assertEqual(quote.sdd_ref, "2.1 Quotation")
        self.assertEqual(quote.requirement_refs, "SAL-01, SAL-02")
        self.assertEqual(quote.model_id.model, "res.partner")
        self.assertEqual(quote.lane_id.name, "Sales")
        self.assertEqual(quote.version_in_id, process.current_version_id)
        self.assertFalse(quote.manual_link)
        self.assertEqual(self._element("Task_Sample_Invoice").status, "proposal")
        self.assertEqual(
            process.current_version_id.diff_summary,
            "First version: 6 elements in 2 lanes.",
        )
        self.assertIn("<br>", process.message_ids[0].body)
        # Same file again: nothing new.
        self.assertEqual(self._import(self.xml)["status"], "unchanged")
        self.assertEqual(len(process.version_ids), 1)

    def test_new_version_keeps_comments_and_status(self):
        self._import(self.xml)
        process = self._process()
        quote = self._element("Task_Sample_Quote")
        quote.with_user(self.user).post_comment("Check the price list")
        quote.with_user(self.manager).status = "open"
        lost = self._element("End_Sample_Lost")
        new = edit(self.xml, rename("Task_Sample_Quote", "Send quote"))
        new = edit(new, set_doc("Task_Sample_Quote", "sdd: 2.2\nstatus: decidido"))
        new = edit(new, remove_element("End_Sample_Lost"))
        new = edit(
            new,
            add_task_after(
                "Task_Sample_Quote", "Task_Sample_Check", "Check", "Lane_Sample_Sales"
            ),
        )
        result = self._import(new, note="workshop 2")
        self.assertEqual(result["status"], "updated")
        self.assertEqual(process.current_version_id.number, 2)
        self.assertEqual(quote.name, "Send quote")
        self.assertEqual(quote.sdd_ref, "2.2")
        self.assertEqual(quote.status, "open", "status belongs to Odoo")
        self.assertIn("Check the price list", "".join(quote.message_ids.mapped("body")))
        self.assertFalse(lost.active)
        self.assertEqual(lost.version_out_id, process.current_version_id)
        self.assertTrue(self._element("Task_Sample_Check"))
        summary = process.current_version_id.diff_summary
        self.assertIn("Check (Task_Sample_Check)", summary)
        self.assertIn("Removed", summary)
        self.assertIn("Status kept in Odoo", summary)

    def test_version_is_immutable(self):
        self._import(self.xml)
        version = self._process().current_version_id
        with self.assertRaises(UserError):
            version.write({"note": "changed"})
        with self.assertRaises(UserError):
            version.sudo().write({"xml": "x"})
        with self.assertRaises(UserError):
            version.sudo().unlink()
        with self.assertRaises(UserError):
            self._process().sudo().unlink()

    def test_restore(self):
        self._import(self.xml)
        self._import(edit(self.xml, rename("Task_Sample_Quote", "Changed")))
        process = self._process()
        first = process.version_ids.filtered(lambda v: v.number == 1)
        first.with_user(self.manager).action_restore()
        self.assertEqual(process.current_version_id.number, 3)
        self.assertEqual(process.current_version_id.origin, "restore")
        self.assertEqual(self._element("Task_Sample_Quote").name, "Send quotation")

    def test_edit_lock_and_save(self):
        self._import(self.xml)
        process = self._process()
        self.assertTrue(process.with_user(self.manager).acquire_edit_lock()["ok"])
        other = process.with_user(self.manager2).acquire_edit_lock()
        self.assertFalse(other["ok"])
        self.assertEqual(other["user"], self.manager.name)
        with self.assertRaises(UserError):
            process.with_user(self.manager2).save_edited_xml(self.xml)
        with self.assertRaises(AccessError):
            process.with_user(self.user).acquire_edit_lock()
        # Imports wait while someone edits.
        locked = self.Process.with_user(self.manager2).import_xml(
            "sample", edit(self.xml, rename("Task_Sample_Quote", "X"))
        )
        self.assertEqual(locked["status"], "locked")
        drawn = edit(self.xml, move("Task_Sample_Quote", dx=30))
        with self.assertRaises(UserError):
            process.with_user(self.manager).save_edited_xml(
                edit(drawn, remove_element("Task_Sample_Invoice")).replace(
                    "Task_Sample_Quote</bpmn:flowNodeRef>", "Gone</bpmn:flowNodeRef>"
                )
            )
        result = process.with_user(self.manager).save_edited_xml(drawn, "moved")
        self.assertEqual(result["version"], 2)
        self.assertEqual(process.source, "odoo")
        self.assertEqual(process.current_version_id.origin, "edit")
        self.assertIn(
            "Task_Sample_Quote", process.current_version_id.get_diff()["moved"]
        )
        self.assertFalse(process.lock_user_id)
        # A manager can break somebody else's lock.
        process.with_user(self.manager).acquire_edit_lock()
        process.with_user(self.manager2).action_break_lock()
        self.assertFalse(process.lock_user_id)

    def test_import_merges_with_odoo_edits(self):
        self._import(self.xml)
        process = self._process()
        process.with_user(self.manager).acquire_edit_lock()
        ours = edit(self.xml, move("Task_Sample_Invoice", dy=10))
        ours = edit(ours, rename("Gateway_Sample_Approved", "Approved by customer?"))
        process.with_user(self.manager).save_edited_xml(ours)
        theirs = edit(self.xml, rename("Task_Sample_Quote", "Send quote"))
        result = self._import(theirs, note="from the generator")
        self.assertEqual(result["status"], "merged")
        self.assertEqual(result["incoming_version"], 3)
        self.assertEqual(result["version"], 4)
        merged = process.current_version_id
        self.assertEqual(merged.origin, "merge")
        self.assertEqual(merged.merge_parent_id.number, 3)
        self.assertEqual(merged.parent_id.number, 2)
        self.assertFalse(
            process.version_ids.filtered(lambda v: v.number == 3).is_current
        )
        self.assertEqual(self._element("Task_Sample_Quote").name, "Send quote")
        self.assertEqual(
            self._element("Gateway_Sample_Approved").name, "Approved by customer?"
        )
        model = bx.read_model(merged.xml)
        invoice = next(
            e for e in model["elements"] if e["bpmn_id"] == "Task_Sample_Invoice"
        )
        self.assertEqual(invoice["bounds"]["y"], 355)
        # Next file is based on the last file received (v3): a conflict.
        process.with_user(self.manager).acquire_edit_lock()
        process.with_user(self.manager).save_edited_xml(
            edit(merged.xml, rename("Task_Sample_Quote", "Odoo name"))
        )
        theirs2 = edit(theirs, rename("Task_Sample_Quote", "File name"))
        result = self._import(theirs2)
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["base_version"], 3)
        self.assertEqual(result["conflicts"][0]["key"], "Task_Sample_Quote:attrs")
        result = self._import(
            theirs2, resolutions={"Task_Sample_Quote:attrs": "theirs"}
        )
        self.assertEqual(result["status"], "merged")
        self.assertEqual(self._element("Task_Sample_Quote").name, "File name")
        self.assertIn("Conflicts resolved", process.current_version_id.diff_summary)

    def test_wizard_conflict_flow(self):
        self._import(self.xml)
        process = self._process()
        process.with_user(self.manager).acquire_edit_lock()
        process.with_user(self.manager).save_edited_xml(
            edit(self.xml, rename("Task_Sample_Quote", "Odoo"))
        )
        theirs = edit(self.xml, rename("Task_Sample_Quote", "File"))
        wizard = (
            self.env["bpmn.import.wizard"]
            .with_user(self.manager)
            .create(
                {
                    "code": "sample",
                    "file": base64.b64encode(theirs.encode()),
                    "filename": "sample.bpmn",
                }
            )
        )
        wizard.action_import()
        self.assertEqual(wizard.state, "conflict")
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.line_ids.choice = "ours"
        action = wizard.action_import()
        self.assertEqual(action["tag"], "bpmn_process.viewer")
        self.assertEqual(self._element("Task_Sample_Quote").name, "Odoo")
        self.assertEqual(process.current_version_id.origin, "merge")

    def test_access_rights(self):
        self._import(self.xml)
        quote = self._element("Task_Sample_Quote")
        as_user = quote.with_user(self.user)
        self.assertTrue(as_user.post_comment("A question"))
        panel = as_user.get_panel_data()
        self.assertTrue(panel["messages"])
        self.assertEqual(panel["odoo_label"], quote.model_id.name)
        self.assertIn("res.partner", quote.process_id.with_user(self.user).export_xml())
        with self.assertRaises(AccessError):
            as_user.write({"status": "open"})
        with self.assertRaises(AccessError):
            self.env["bpmn.process"].with_user(self.user).import_xml("other", self.xml)
        quote.with_user(self.manager).write({"status": "open"})
        self.env.cr.precommit.run()  # write the tracking values
        self.assertIn(
            "Status",
            "".join(
                str(v["field"])
                for m in as_user.get_panel_data()["messages"]
                for v in m["tracking"]
            ),
        )

    def test_links_and_tests(self):
        self._import(self.xml)
        quote = self._element("Task_Sample_Quote")
        action = quote.action_open_odoo()
        self.assertEqual(action["res_model"], "res.partner")
        quote.with_user(self.manager).menu_id = self.env["ir.ui.menu"].search(
            [], limit=1
        )
        self.assertTrue(quote.manual_link)
        Test = self.env["bpmn.element.test"].with_user(self.manager)
        result = Test.record_results(
            [
                {"bpmn_id": "Task_Sample_Quote", "scenario": "s1", "result": "passed"},
                {
                    "bpmn_id": "Task_Sample_Invoice",
                    "process": "sample",
                    "scenario": "s2",
                    "result": "failed",
                    "environment": "hml",
                },
                {"bpmn_id": "Task_Missing", "scenario": "s3", "result": "passed"},
            ]
        )
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["unknown"], ["Task_Missing"])
        self.assertEqual(quote.test_state, "passed")
        invoice = self._element("Task_Sample_Invoice")
        self.assertEqual(invoice.test_state, "failed")
        Test.record_results(
            [{"bpmn_id": "Task_Sample_Invoice", "scenario": "s2", "result": "passed"}]
        )
        invoice.invalidate_recordset(["test_state"])
        self.assertEqual(invoice.test_state, "passed")

    def test_viewer_data_and_export(self):
        self._import(self.xml)
        process = self._process()
        lane = process.lane_ids.filtered(lambda la: la.bpmn_id == "Lane_Sample_Billing")
        lane.group_ids = self.env.ref("bpmn_process.group_bpmn_user")
        quote = self._element("Task_Sample_Quote")
        quote.with_user(self.user).post_comment("Hello")
        data = process.with_user(self.user).get_viewer_data()
        self.assertEqual(data["version"]["number"], 1)
        self.assertEqual(data["elements"]["Task_Sample_Quote"]["messages"], 1)
        self.assertTrue(data["elements"]["Task_Sample_Invoice"]["mine"])
        self.assertFalse(data["elements"]["Task_Sample_Quote"]["mine"])
        self.assertFalse(data["can_manage"])
        self._import(edit(self.xml, rename("Task_Sample_Quote", "New")))
        first = process.version_ids.filtered(lambda v: v.number == 1)
        data = process.get_viewer_data(compare_version_id=first.id)
        self.assertEqual(data["diff"]["changed"], {"Task_Sample_Quote": ["attrs"]})
        quote.with_user(self.manager).write(
            {"status": "open", "requirement_refs": "SAL-09"}
        )
        exported = process.export_xml()
        info = bx.read_model(exported)
        quote_info = next(
            e for e in info["elements"] if e["bpmn_id"] == "Task_Sample_Quote"
        )
        self.assertEqual(quote_info["status"], "open")
        self.assertEqual(quote_info["requirements"], "SAL-09")
        self.assertEqual(quote_info["odoo"], "res.partner")
        self.assertFalse(bx.validate(exported))
        self.assertEqual(
            self.env["bpmn.process"].export_by_code("sample")["version"], 2
        )

    def test_invalid_file(self):
        with self.assertRaises(UserError):
            self._import("<definitions/>")
