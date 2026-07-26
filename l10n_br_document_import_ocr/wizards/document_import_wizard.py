# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import MODELO_FISCAL_NFSE

from ..models.import_binding import OcrDocumentBinding
from ..models.ocr_engine import sniff_mimetype

LOW_CONFIDENCE = 0.7

FIELD_LABELS = {
    "issuer_cnpj": "CNPJ do emissor",
    "document_number": "Número do documento",
    "document_date": "Data de emissão",
    "amount_untaxed": "Valor dos serviços",
    "amount_total": "Valor total",
    "issqn_value": "Valor do ISS",
    "issqn_wh_value": "ISS retido",
}


class DocumentImportWizard(models.TransientModel):
    _inherit = "l10n_br_fiscal.document.import.wizard"

    extraction_id = fields.Many2one(
        comodel_name="l10n_br.document.import.extraction",
        string="Extração",
        readonly=True,
    )
    is_ocr_import = fields.Boolean(readonly=True)
    document_date = fields.Date()
    verify_code = fields.Char(string="Código de verificação")
    amount_untaxed = fields.Float(string="Valor dos serviços")
    amount_total = fields.Float(string="Valor total")
    issqn_value = fields.Float(string="Valor do ISS")
    issqn_wh_value = fields.Float(string="ISS retido")
    service_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.service.type",
        string="Código de serviço (LC 116)",
        domain=[("internal_type", "=", "normal")],
    )
    service_description = fields.Char(string="Descrição do serviço")
    low_confidence_fields = fields.Char(readonly=True)
    ocr_destination = fields.Selection(
        selection=[
            ("fiscal", "Somente Documento Fiscal"),
            ("move", "Documento Fiscal + Fatura"),
        ],
        string="Destino",
        default=lambda self: self.env.company.document_import_destination,
    )

    # ------------------------------------------------------------------
    # Pipeline: detecção e parsing
    # ------------------------------------------------------------------

    @api.model
    def _parse_file_data(self, file_data):
        raw = base64.b64decode(file_data)
        if sniff_mimetype(raw):
            extraction = self.env[
                "l10n_br.document.import.extraction"
            ].get_or_create_for_file(file_data)
            return OcrDocumentBinding(
                extraction.structured_data,
                extraction.raw_text,
                extraction.field_confidence,
                extraction.id,
            )
        return super()._parse_file_data(file_data)

    @api.model
    def _detect_binding(self, binding):
        if getattr(binding, "br_ocr_import", False):
            # DANFE/NFC-e escaneada tem chave de 44; NFS-e municipal não.
            # No MVP ambos entram como nota de serviço apenas quando não há
            # chave; com chave, orientamos a importar o XML.
            if binding.data.get("document_key"):
                raise UserError(
                    _(
                        "Este documento tem chave de acesso (%s): importe o "
                        "XML correspondente (via DF-e ou upload do XML) em "
                        "vez da imagem."
                    )
                    % binding.data["document_key"]
                )
            return self._detect_document_type(MODELO_FISCAL_NFSE)
        return super()._detect_binding(binding)

    def _extract_binding_data(self, binding):
        if not getattr(binding, "br_ocr_import", False):
            return super()._extract_binding_data(binding)
        data = binding.data
        self.is_ocr_import = True
        self.extraction_id = binding.extraction_id
        self.issuer_cnpj = data.get("issuer_cnpj")
        if self.issuer_cnpj:
            self.issuer_partner_id = self._search_partner(cnpj=self.issuer_cnpj)
            if self.issuer_partner_id:
                self.extraction_id.partner_id = self.issuer_partner_id
        self.document_number = data.get("document_number")
        self.rps_number = data.get("rps_number")
        self.verify_code = data.get("verify_code")
        self.document_date = data.get("document_date")
        self.amount_untaxed = data.get("amount_untaxed", 0.0)
        self.amount_total = data.get("amount_total", 0.0)
        self.issqn_value = data.get("issqn_value", 0.0)
        self.issqn_wh_value = data.get("issqn_wh_value", 0.0)
        if data.get("service_code"):
            self.service_type_id = self.env["l10n_br_fiscal.service.type"].search(
                [("code", "=", data["service_code"])], limit=1
            )
        self.fiscal_operation_id = self._find_fiscal_operation_service()
        self._set_low_confidence_fields(binding.confidence)

    def _set_low_confidence_fields(self, confidence):
        low = [
            FIELD_LABELS[field]
            for field, value in (confidence or {}).items()
            if field in FIELD_LABELS and value < LOW_CONFIDENCE
        ]
        self.low_confidence_fields = ", ".join(low)

    def _destination_partner_from_binding(self, binding):
        if getattr(binding, "br_ocr_import", False):
            self.destination_partner_id = self.company_id.partner_id
            return
        return super()._destination_partner_from_binding(binding)

    # ------------------------------------------------------------------
    # Operação fiscal e dedupe (NFS-e não tem CFOP nem chave)
    # ------------------------------------------------------------------

    def _find_fiscal_operation_service(self):
        default = self.company_id.document_import_default_operation_id
        if default:
            return default
        line = self.env["l10n_br_fiscal.operation.line"].search(
            [
                ("state", "=", "approved"),
                ("fiscal_operation_type", "=", "in"),
                ("tax_icms_or_issqn", "=", "issqn"),
            ],
            limit=1,
        )
        return line.fiscal_operation_id

    def _find_existing_document(self):
        if not self.is_ocr_import:
            return super()._find_existing_document()
        domain = [
            ("document_type_id.code", "=", MODELO_FISCAL_NFSE),
            ("document_number", "=", self.document_number or ""),
        ]
        if self.issuer_partner_id:
            domain.append(("partner_id", "=", self.issuer_partner_id.id))
        if self.document_number:
            self.document_id = self.env["l10n_br_fiscal.document"].search(
                domain, limit=1
            )

    # ------------------------------------------------------------------
    # Criação do documento
    # ------------------------------------------------------------------

    def _create_edoc_from_file(self):
        binding = self._parse_file()
        if not getattr(binding, "br_ocr_import", False):
            return super()._create_edoc_from_file()
        edoc = self.env["l10n_br_fiscal.document"].create(
            self._prepare_ocr_edoc_values()
        )
        self._create_ocr_edoc_line(edoc)
        self._attach_original_file_to_document(edoc)
        self.extraction_id.document_id = edoc
        return binding, edoc

    def _prepare_ocr_edoc_values(self):
        if not self.fiscal_operation_id:
            raise UserError(
                _(
                    "Nenhuma operação fiscal de entrada de serviço "
                    "encontrada. Configure a operação padrão nas "
                    "configurações fiscais."
                )
            )
        return {
            "company_id": self.company_id.id,
            "fiscal_operation_id": self.fiscal_operation_id.id,
            "fiscal_operation_type": "in",
            "issuer": "partner",
            "document_type_id": self.document_type_id.id,
            "partner_id": self.issuer_partner_id.id,
            "document_number": self.document_number,
            "rps_number": self.rps_number,
            "document_serie": self.document_serie or "1",
            "document_date": self.document_date,
            "imported_document": True,
        }

    def _create_ocr_edoc_line(self, edoc):
        operation_line = self.fiscal_operation_id.line_definition(
            self.company_id, self.issuer_partner_id, self.env["product.product"]
        )
        if not operation_line:
            operation_line = self.fiscal_operation_id.line_ids.filtered(
                lambda line: line.state == "approved"
                and line.tax_icms_or_issqn == "issqn"
            )[:1]
        if not operation_line:
            operation_line = self.fiscal_operation_id.line_ids[:1]
        self.env["l10n_br_fiscal.document.line"].create(
            {
                "document_id": edoc.id,
                "name": self.service_description
                or _("Serviço importado (OCR) - NFS-e %s")
                % (self.document_number or ""),
                "fiscal_operation_id": self.fiscal_operation_id.id,
                "fiscal_operation_line_id": operation_line.id,
                "fiscal_operation_type": "in",
                "quantity": 1.0,
                "price_unit": self.amount_untaxed or self.amount_total,
                "service_type_id": self.service_type_id.id,
                "issqn_value": self.issqn_value,
                "issqn_wh_value": self.issqn_wh_value,
            }
        )

    def _attach_original_file_to_document(self, edoc):
        extraction = self.extraction_id
        self.env["ir.attachment"].create(
            {
                "name": extraction.name or "documento-importado",
                "datas": self.file,
                "res_model": "l10n_br_fiscal.document",
                "res_id": edoc.id,
                "mimetype": extraction.mimetype,
            }
        )

    # ------------------------------------------------------------------
    # Confirmação com destino configurável
    # ------------------------------------------------------------------

    def action_confirm_ocr_import(self):
        self.ensure_one()
        if self.document_id:
            raise UserError(
                _("Já existe um documento com este número deste fornecedor.")
            )
        if not self.issuer_partner_id:
            raise UserError(
                _(
                    "Fornecedor não localizado pelo CNPJ %s. Cadastre o "
                    "parceiro e importe novamente."
                )
                % (self.issuer_cnpj or "-")
            )
        if self.ocr_destination == "move":
            return self.action_import_and_open_move()
        return self.action_import_and_open_document()
