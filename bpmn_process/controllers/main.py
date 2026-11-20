# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import content_disposition, request


class BpmnProcessController(http.Controller):
    def _xml_response(self, xml, filename):
        return request.make_response(
            xml,
            headers=[
                ("Content-Type", "application/xml; charset=utf-8"),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

    @http.route("/bpmn_process/export/<int:process_id>", type="http", auth="user")
    def export_process(self, process_id, **kwargs):
        process = request.env["bpmn.process"].browse(process_id).exists()
        if not process:
            raise request.not_found()
        process.check_access("read")
        return self._xml_response(process.export_xml(), "%s.bpmn" % process.code)

    @http.route("/bpmn_process/version/<int:version_id>", type="http", auth="user")
    def export_version(self, version_id, **kwargs):
        version = request.env["bpmn.process.version"].browse(version_id).exists()
        if not version:
            raise request.not_found()
        version.check_access("read")
        return self._xml_response(
            version.xml, "%s-v%s.bpmn" % (version.process_id.code, version.number)
        )
