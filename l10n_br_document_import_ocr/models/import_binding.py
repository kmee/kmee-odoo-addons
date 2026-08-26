# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


class OcrDocumentBinding:
    """Resultado da extração OCR no formato de "binding".

    O wizard de importação da l10n_br_fiscal trabalha com objetos (bindings
    xsdata dos XMLs). Esta classe imita esse contrato para o pipeline OCR:
    os wizards especializados testam atributos via hasattr/getattr, então o
    marcador ``br_ocr_import`` identifica este binding sem colidir com os
    testes ``hasattr(binding, "infNFe")`` dos módulos de NF-e/CT-e/MDF-e.
    """

    br_ocr_import = True

    def __init__(self, data, raw_text, confidence, extraction_id):
        # dict com os campos estruturados extraídos (ver document_extractor)
        self.data = data or {}
        # texto integral extraído do documento (camada nativa ou OCR)
        self.raw_text = raw_text or ""
        # dict {campo: 0..1}
        self.confidence = confidence or {}
        # id do registro de cache/log (l10n_br.document.import.extraction)
        self.extraction_id = extraction_id
