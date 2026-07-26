# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import base64
import os
from unittest import mock

from xsdata.exceptions import ParserError

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_br_document_import_ocr.models.ocr_engine import OcrEngine

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
FAKE_PDF = base64.b64encode(b"%PDF-1.4 conteudo-fake-para-teste")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


@tagged("post_install", "-at_install")
class TestOcrImportWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.cnpj_cpf = "30.360.463/0001-25"
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Servicos Digitais Exemplo",
                "legal_name": "SERVICOS DIGITAIS EXEMPLO LTDA",
                "is_company": True,
                "cnpj_cpf": "04.391.789/0001-00",
                "country_id": cls.env.ref("base.br").id,
            }
        )
        cls.text = fixture("nfse_sp_texto.txt")

    def _make_wizard(self):
        return (
            self.env["l10n_br_fiscal.document.import.wizard"]
            .with_company(self.company)
            .create({})
        )

    def _fill(self, wizard):
        with mock.patch.object(
            OcrEngine, "extract_text", return_value=(self.text, "ocr")
        ) as mocked:
            wizard.file = FAKE_PDF
            wizard._onchange_file()
        return mocked

    def test_onchange_preenche_preview(self):
        wizard = self._make_wizard()
        self._fill(wizard)
        self.assertTrue(wizard.is_ocr_import)
        self.assertEqual(wizard.issuer_partner_id, self.partner)
        self.assertEqual(wizard.document_number, "00012345")
        self.assertEqual(wizard.verify_code, "ABCD-EFGH")
        self.assertEqual(wizard.amount_untaxed, 10000.00)
        self.assertEqual(wizard.amount_total, 9385.00)
        self.assertEqual(wizard.issqn_value, 200.00)
        self.assertTrue(wizard.fiscal_operation_id)
        self.assertEqual(str(wizard.document_date), "2026-07-15")

    def test_destino_fiscal_cria_documento(self):
        wizard = self._make_wizard()
        self._fill(wizard)
        wizard.ocr_destination = "fiscal"
        wizard.action_confirm_ocr_import()
        edoc = wizard.document_id
        self.assertTrue(edoc)
        self.assertEqual(edoc.document_type_id.code, "SE")
        self.assertEqual(edoc.partner_id, self.partner)
        self.assertTrue(edoc.imported_document)
        self.assertEqual(len(edoc.fiscal_line_ids), 1)
        line = edoc.fiscal_line_ids
        self.assertEqual(line.price_unit, 10000.00)
        # arquivo original anexado ao documento
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "l10n_br_fiscal.document"),
                ("res_id", "=", edoc.id),
            ]
        )
        self.assertTrue(attachment)

    def test_destino_move_cria_fatura(self):
        wizard = self._make_wizard()
        self._fill(wizard)
        wizard.ocr_destination = "move"
        action = wizard.action_confirm_ocr_import()
        move = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.partner_id, self.partner)
        self.assertTrue(move.fiscal_document_id)
        self.assertEqual(move.fiscal_document_id, wizard.document_id)

    def test_cache_extrai_uma_vez(self):
        """Entre o onchange e a confirmação, o OCR roda uma única vez."""
        wizard = self._make_wizard()
        mocked = self._fill(wizard)
        self.assertEqual(mocked.call_count, 1)
        wizard.ocr_destination = "fiscal"
        with mock.patch.object(
            OcrEngine, "extract_text", return_value=(self.text, "ocr")
        ) as second:
            wizard.action_confirm_ocr_import()
        self.assertEqual(second.call_count, 0)

    def test_dedupe_por_numero_e_fornecedor(self):
        wizard = self._make_wizard()
        self._fill(wizard)
        wizard.ocr_destination = "fiscal"
        wizard.action_confirm_ocr_import()
        duplicate = self._make_wizard()
        self._fill(duplicate)
        self.assertTrue(duplicate.document_id)
        with self.assertRaises(UserError):
            duplicate.action_confirm_ocr_import()

    def test_xml_segue_para_o_fluxo_padrao(self):
        """Arquivo XML não entra no pipeline OCR (vai para o XmlParser)."""
        wizard = self._make_wizard()
        xml = base64.b64encode(b"<?xml version='1.0'?><nota><x>1</x></nota>")
        with self.assertRaises(ParserError):
            # sem módulo de NF-e instalado, a cadeia base rejeita o binding;
            # o essencial é NÃO cair no fluxo OCR
            wizard.file = xml
            wizard._onchange_file()
        self.assertFalse(wizard.is_ocr_import)
