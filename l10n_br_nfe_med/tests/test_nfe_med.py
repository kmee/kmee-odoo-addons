# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNfeMed(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.nfe = cls.env.ref("l10n_br_nfe.demo_nfe_natural_icms_18_red_51_11")
        cls.nfe._register_hook()
        cls.nfe.nfe40_detPag = [
            Command.clear(),
            Command.create(
                {
                    "nfe40_indPag": "0",
                    "nfe40_tPag": "01",
                    "nfe40_vPag": cls.nfe.amount_financial_total,
                },
            ),
        ]
        cls.nfe.action_document_confirm()
        cls.line = cls.nfe.fiscal_line_ids[0]
        cls.med = cls.env["nfe.40.med"].create(
            {"nfe40_cProdANVISA": "1234567890123", "nfe40_vPMC": 25.5}
        )

    def _det_med(self):
        """Return {det nItem: med element} of the exported NF-e XML."""
        xml = self.nfe.serialize()[0].to_xml()
        root = etree.fromstring(xml.encode())
        result = {}
        for det in root.iter("{*}det"):
            meds = det.findall("{*}prod/{*}med")
            result[det.get("nItem")] = meds[0] if meds else None
        return result

    def test_med_group_is_stored_on_product(self):
        """
        Given a product
        When a medicine group (ANVISA registry and maximum consumer price) is set
        Then the product keeps it, and a product without group has none
        """
        product = self.line.product_id
        self.assertFalse(product.nfe40_med)
        product.nfe40_med = self.med
        self.assertEqual(product.nfe40_med.nfe40_cProdANVISA, "1234567890123")
        self.assertEqual(product.product_tmpl_id.nfe40_med, self.med)

    def test_fiscal_line_follows_product_med_group(self):
        """
        Given a fiscal document line of a product
        When the product receives, changes and loses its medicine group
        Then the line (related field) follows each change
        """
        product = self.line.product_id
        self.assertFalse(self.line.nfe40_med)
        product.nfe40_med = self.med
        self.assertEqual(self.line.nfe40_med, self.med)
        other = self.env["nfe.40.med"].create(
            {
                "nfe40_cProdANVISA": "ISENTO",
                "nfe40_xMotivoIsencao": "RDC 199",
                "nfe40_vPMC": 1,
            }
        )
        product.nfe40_med = other
        self.assertEqual(self.line.nfe40_med, other)
        product.nfe40_med = False
        self.assertFalse(self.line.nfe40_med)

    def test_nfe_xml_has_no_med_without_group(self):
        """
        Given a document whose products have no medicine group
        When the NF-e XML is generated
        Then no det carries a med tag
        """
        self.assertTrue(self.nfe.fiscal_line_ids)
        self.assertTrue(all(med is None for med in self._det_med().values()))

    def test_nfe_xml_exports_med_group_of_the_product(self):
        """
        Given a product with ANVISA registry 1234567890123 and PMC 25.50
        When the NF-e XML is generated
        Then the det of that line has prod/med with cProdANVISA and vPMC,
        and only that det (other lines have none)
        """
        self.line.product_id.nfe40_med = self.med
        det_med = self._det_med()
        with_med = {n: m for n, m in det_med.items() if m is not None}
        self.assertTrue(with_med)
        for med in with_med.values():
            self.assertEqual(med.findtext("{*}cProdANVISA"), "1234567890123")
            self.assertEqual(med.findtext("{*}vPMC"), "25.50")
        self.assertEqual(
            len(with_med),
            len(
                self.nfe.fiscal_line_ids.filtered(
                    lambda line: line.product_id == self.line.product_id
                )
            ),
        )

    def test_nfe_xml_exports_exemption_reason(self):
        """
        Given a medicine exempt from ANVISA registry ('ISENTO' + decision)
        When the NF-e XML is generated
        Then cProdANVISA is ISENTO and xMotivoIsencao has the decision
        """
        exempt = self.env["nfe.40.med"].create(
            {
                "nfe40_cProdANVISA": "ISENTO",
                "nfe40_xMotivoIsencao": "RDC 199/2006",
                "nfe40_vPMC": 10.0,
            }
        )
        self.line.product_id.nfe40_med = exempt
        meds = [m for m in self._det_med().values() if m is not None]
        self.assertTrue(meds)
        self.assertEqual(meds[0].findtext("{*}cProdANVISA"), "ISENTO")
        self.assertEqual(meds[0].findtext("{*}xMotivoIsencao"), "RDC 199/2006")

    def test_product_form_view_has_medicine_group(self):
        """
        Given the product form view
        When it is built
        Then the fiscal tab has the Medicamento group with the nfe40_med field
        """
        user = self.env["res.users"].create(
            {
                "name": "Fiscal user",
                "login": "fiscal_med_user",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("l10n_br_fiscal.group_manager").id,
                        ]
                    )
                ],
            }
        )
        arch = (
            self.env["product.template"]
            .with_user(user)
            .get_view(view_type="form")["arch"]
        )
        root = etree.fromstring(arch.encode())
        fields = root.xpath(
            "//page[@name='fiscal']//group[@name='med']/field[@name='nfe40_med']"
        )
        self.assertEqual(len(fields), 1)

    def test_document_line_form_view_has_medicine_page(self):
        """
        Given the fiscal document line form view
        When it is built
        Then there is a Medicamento page with the nfe40_med field
        """
        arch = self.env["l10n_br_fiscal.document.line"].get_view(
            self.env.ref("l10n_br_fiscal.document_line_form").id, "form"
        )["arch"]
        root = etree.fromstring(arch.encode())
        fields = root.xpath("//page[@name='med']//field[@name='nfe40_med']")
        self.assertEqual(len(fields), 1)
