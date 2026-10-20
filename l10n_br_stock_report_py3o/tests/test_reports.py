# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io
import re
import zipfile

from odoo.tests.common import TransactionCase, tagged


def _odt_text(content):
    """Visible text of a rendered ODT (content.xml without tags)."""
    xml = zipfile.ZipFile(io.BytesIO(content)).read("content.xml").decode()
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))


@tagged("post_install", "-at_install")
class TestStockReportPy3o(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.delivery = cls.env.ref("l10n_br_stock_report_py3o.action_report_delivery")
        cls.picking_report = cls.env.ref(
            "l10n_br_stock_report_py3o.action_report_picking"
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Entrega LTDA", "lang": "en_US"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Produto Entrega", "type": "consu", "is_storable": True}
        )
        picking_type = cls.env.ref("stock.picking_type_out")
        cls.picking = cls.env["stock.picking"].create(
            {
                "partner_id": cls.partner.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                "origin": "SO-ORIGEM-123",
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Produto Entrega",
                            "product_id": cls.product.id,
                            "product_uom_qty": 4,
                            "product_uom": cls.product.uom_id.id,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": cls.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )

    def _render(self, report):
        report.py3o_filetype = "odt"  # native format: no LibreOffice needed
        content, filetype = report._render_py3o(report.report_name, self.picking.ids)
        self.assertEqual(filetype, "odt")
        return _odt_text(content)

    def _deliver(self):
        """Reserve and validate the picking (stock is made available first)."""
        location = self.picking.location_id
        self.env["stock.quant"]._update_available_quantity(self.product, location, 4)
        self.picking.action_confirm()
        self.picking.action_assign()
        return self.picking

    def test_reports_are_registered_as_py3o_on_picking(self):
        """
        Given the module is installed
        When the report actions are read
        Then both are py3o reports of stock.picking with the ODT templates
        shipped by the module
        """
        self.assertEqual(self.delivery.report_type, "py3o")
        self.assertEqual(self.picking_report.report_type, "py3o")
        self.assertEqual(self.delivery.model, "stock.picking")
        self.assertEqual(self.picking_report.model, "stock.picking")
        self.assertEqual(self.delivery.py3o_template_fallback, "report/delivery.odt")
        self.assertEqual(
            self.picking_report.py3o_template_fallback, "report/picking.odt"
        )
        bound = self.env["ir.actions.report"].search([("model", "=", "stock.picking")])
        self.assertIn(self.delivery, bound)
        self.assertIn(self.picking_report, bound)

    def test_delivery_slip_renders_picking_data(self):
        """
        Given a draft outgoing picking with 4 units of a product
        When the delivery slip is rendered
        Then it shows Delivery Order, the state, picking number, origin,
        product and quantity
        """
        text = self._render(self.delivery)
        self.assertIn("Delivery Order draft " + self.picking.name, text)
        self.assertIn("SO-ORIGEM-123", text)
        self.assertIn("Produto Entrega 4.00 Units", text)
        self.assertIn("Scheduled Date", text)
        self.assertNotIn("Incoming Picking", text)

    def test_delivery_slip_of_incoming_picking_is_incoming(self):
        """
        Given an incoming (receipt) picking
        When the delivery slip is rendered
        Then the document title is Incoming Picking
        """
        receipt_type = self.env.ref("stock.picking_type_in")
        self.picking.picking_type_id = receipt_type
        text = self._render(self.delivery)
        self.assertIn("Incoming Picking", text)
        self.assertNotIn("Delivery Order", text)

    def test_done_picking_shows_ship_date_and_no_state(self):
        """
        Given a validated picking
        When the delivery slip is rendered
        Then it shows the ship date instead of the scheduled date
        and the state is not part of the title
        """
        picking = self._deliver()
        self.assertEqual(picking.state, "assigned")
        picking.move_ids.quantity = 4
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        text = self._render(self.delivery)
        self.assertIn("Delivery Order " + picking.name, text)
        self.assertIn("Ship Date", text)
        self.assertNotIn("Scheduled Date", text)

    def test_picking_operations_for_unavailable_stock_warns(self):
        """
        Given a confirmed picking without stock
        When the picking operations report is rendered
        Then it shows the Confirmed state and the warning that products
        could not be reserved
        """
        self.picking.action_confirm()
        text = self._render(self.picking_report)
        self.assertIn("Picking Confirmed " + self.picking.name, text)
        self.assertIn("could not be reserved", text)

    def test_picking_operations_when_reserved_lists_source_location(self):
        """
        Given a picking with reserved stock (assigned)
        When the picking operations report is rendered
        Then the title has no state, the source location is listed and the
        unavailable-stock warning is gone
        """
        picking = self._deliver()
        self.assertEqual(picking.state, "assigned")
        text = self._render(self.picking_report)
        self.assertIn("Picking " + picking.name, text)
        self.assertNotIn("Picking Assigned", text)
        self.assertNotIn("could not be reserved", text)
        self.assertIn(picking.location_id.display_name, text)

    def test_user_without_language_gets_brazilian_titles(self):
        """
        Given a user without language
        When the reports are rendered
        Then the titles are Portuguese (templates fall back to pt_BR)
        """
        self.env.user.lang = False
        self.assertIn("Pedido de entrega", self._render(self.delivery))
        self.assertIn("Separa\u00e7\u00e3o", self._render(self.picking_report))

    def test_download_file_names(self):
        """
        Given a picking of customer 'Cliente Entrega LTDA'
        When the download names are computed
        Then the slip is 'Delivery Slip - <customer> - <picking>' and the picking
        operations is 'Pick-<picking with _>-<customer with _>.pdf'
        """
        self.assertEqual(
            self.delivery.gen_report_download_filename(self.picking.ids, {}),
            "Delivery Slip - Cliente Entrega LTDA - %s" % self.picking.name,
        )
        self.assertEqual(
            self.picking_report.gen_report_download_filename(self.picking.ids, {}),
            "Pick-%s-Cliente_Entrega_LTDA.pdf" % self.picking.name.replace("/", "_"),
        )
