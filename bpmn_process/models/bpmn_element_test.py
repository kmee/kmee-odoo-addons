# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class BpmnElementTest(models.Model):
    _name = "bpmn.element.test"
    _description = "BPMN Element Test Result"
    _order = "date desc, id desc"

    element_id = fields.Many2one(
        "bpmn.element", required=True, ondelete="cascade", index=True
    )
    process_id = fields.Many2one(
        related="element_id.process_id", store=True, index=True
    )
    company_id = fields.Many2one(related="element_id.company_id", store=True)
    scenario = fields.Char(required=True)
    environment = fields.Char()
    result = fields.Selection(
        [("passed", "Passed"), ("failed", "Failed"), ("skipped", "Skipped")],
        required=True,
    )
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    evidence_url = fields.Char(string="Evidence")
    note = fields.Text()

    @api.model
    def record_results(self, results):
        """Record end-to-end test results by BPMN id.

        ``results`` is a list of dicts with ``bpmn_id``, ``scenario`` and
        ``result`` (passed, failed or skipped), and optionally ``process``
        (process code), ``environment``, ``evidence_url``, ``note`` and
        ``date``. The BPMN id is the ``@bpmn:<id>`` tag of the scenario.
        """
        Element = self.env["bpmn.element"]
        created = self.browse()
        unknown, ambiguous = [], []
        for item in results:
            domain = [("bpmn_id", "=", item["bpmn_id"])]
            if item.get("process"):
                domain.append(("process_id.code", "=", item["process"]))
            elements = Element.search(domain)
            if not elements:
                unknown.append(item["bpmn_id"])
                continue
            if len(elements) > 1:
                ambiguous.append(item["bpmn_id"])
                continue
            vals = {
                "element_id": elements.id,
                "scenario": item["scenario"],
                "result": item["result"],
            }
            for key in ("environment", "evidence_url", "note", "date"):
                if item.get(key):
                    vals[key] = item[key]
            created |= self.create(vals)
        return {"created": len(created), "unknown": unknown, "ambiguous": ambiguous}
