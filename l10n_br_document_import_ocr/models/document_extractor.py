# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging
import re

from erpbrasil.base.fiscal.cnpj_cpf import validar_cnpj, validar_cpf
from erpbrasil.base.misc import punctuation_rm

from odoo import models

_logger = logging.getLogger(__name__)

CNPJ_CPF_RE = re.compile(
    r"\b(\d{2}\.?\d{3}\.?\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}|\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b"
)
ACCESS_KEY_RE = re.compile(r"\b(\d[\d\s.]{42,60}\d)\b")
DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
MONEY_RE = r"R?\$?\s*([\d.]+,\d{2})"

# Âncoras (keyword -> campo). A primeira âncora que casar vence; a busca é
# feita rótulo + valor monetário na mesma linha ou na seguinte.
MONEY_ANCHORS = [
    ("amount_total", r"valor\s+(?:total|l[ií]quido)\s+da\s+nota"),
    ("amount_total", r"valor\s+l[ií]quido"),
    ("amount_untaxed", r"valor\s+(?:total\s+)?d[oe]s?\s+servi[çc]os?"),
    ("issqn_base", r"base\s+de\s+c[áa]lculo"),
    ("issqn_value", r"valor\s+do\s+iss(?!\s*retido)"),
    ("issqn_wh_value", r"iss\s+retido"),
    ("irpj_wh_value", r"\birr?f\b"),
    ("csll_wh_value", r"\bcsll\b"),
    ("pis_wh_value", r"\bpis(?:/pasep)?\b"),
    ("cofins_wh_value", r"\bcofins\b"),
    ("inss_wh_value", r"\binss\b"),
]

NUMBER_ANCHORS = [
    ("document_number", r"n[úu]mero\s+da\s+(?:nota|nfs-?e)\s*:?\s*(\d+)"),
    ("document_number", r"n[º°]\s*da\s+nfs-?e\s*:?\s*(\d+)"),
    ("document_number", r"nfs-?e\s+n[º°.:]*\s*(\d+)"),
    ("verify_code", r"c[óo]digo\s+de\s+verifica[çc][ãa]o\s*:?\s*([A-Z0-9.-]{4,20})"),
    ("rps_number", r"\brps\b[^\d]{0,20}(\d+)"),
    (
        "service_code",
        r"(?:c[óo]digo\s+do\s+servi[çc]o|item\s+da\s+lista)"
        r"[^\d]{0,10}(\d{1,2}\.?\d{2})",
    ),
]


def parse_money_br(value):
    """'1.234,56' -> 1234.56"""
    return float(value.replace(".", "").replace(",", "."))


class DocumentExtractor(models.AbstractModel):
    _name = "l10n_br.document.extractor"
    _description = "Extração estruturada de campos fiscais brasileiros"

    def extract(self, text, company):
        """Extrai os campos estruturados do texto do documento.

        :return: (data: dict, confidence: dict, method: str)
        """
        data, confidence = self._extract_generic(text, company)
        # Hooks de fases futuras: templates por parceiro/prefeitura e
        # fallback LLM entram aqui, mesclando campo a campo por confiança.
        return data, confidence, "regex"

    def _extract_generic(self, text, company):
        data = {}
        confidence = {}
        lower = text.lower()

        self._extract_partners(text, company, data, confidence)
        self._extract_access_key(text, data, confidence)
        self._extract_numbers(lower, text, data, confidence)
        self._extract_dates(text, data, confidence)
        self._extract_money(lower, data, confidence)
        self._reconcile(data, confidence)
        return data, confidence

    def _extract_partners(self, text, company, data, confidence):
        """CNPJs com DV válido; o que difere do CNPJ da empresa é o emissor."""
        company_cnpj = punctuation_rm(company.cnpj_cpf or "")
        seen = []
        for match in CNPJ_CPF_RE.finditer(text):
            digits = punctuation_rm(re.sub(r"\s", "", match.group(1)))
            if digits in seen:
                continue
            if not (validar_cnpj(digits) or validar_cpf(digits)):
                continue
            seen.append(digits)
        issuers = [d for d in seen if d != company_cnpj]
        if issuers:
            data["issuer_cnpj"] = issuers[0]
            confidence["issuer_cnpj"] = 1.0
        if company_cnpj in seen:
            data["destination_cnpj"] = company_cnpj
            confidence["destination_cnpj"] = 1.0

    def _extract_access_key(self, text, data, confidence):
        """Chave de acesso de 44 dígitos (DANFE/NFC-e escaneada)."""
        for match in ACCESS_KEY_RE.finditer(text):
            digits = re.sub(r"[\s.]", "", match.group(1))
            if len(digits) == 44 and digits.isdigit():
                data["document_key"] = digits
                confidence["document_key"] = 0.9
                return

    def _extract_numbers(self, lower, text, data, confidence):
        for field, pattern in NUMBER_ANCHORS:
            if field in data:
                continue
            match = re.search(pattern, lower, re.IGNORECASE)
            if match:
                # recupera o trecho original (case) pela posição
                value = text[match.start(1) : match.end(1)].strip()
                data[field] = value
                confidence[field] = 0.8

    def _extract_dates(self, text, data, confidence):
        dates = []
        for match in DATE_RE.finditer(text):
            day, month, year = map(int, match.groups())
            if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2099:
                dates.append("%04d-%02d-%02d" % (year, month, day))
        if dates:
            # A primeira data plausível do documento costuma ser a emissão.
            data["document_date"] = dates[0]
            confidence["document_date"] = 0.6

    def _extract_money(self, lower, data, confidence):
        for field, anchor in MONEY_ANCHORS:
            if field in data:
                continue
            match = re.search(
                anchor + r"[^\d]{0,40}?" + MONEY_RE, lower, re.IGNORECASE | re.DOTALL
            )
            if match:
                data[field] = parse_money_br(match.group(1))
                confidence[field] = 0.7

    def _reconcile(self, data, confidence):
        """Consistência aritmética eleva/derruba confiança dos totais."""
        untaxed = data.get("amount_untaxed")
        total = data.get("amount_total")
        if untaxed is None and total is not None:
            data["amount_untaxed"] = total
            confidence["amount_untaxed"] = confidence.get("amount_total", 0.5) * 0.8
            return
        if untaxed is not None and total is None:
            data["amount_total"] = untaxed
            confidence["amount_total"] = confidence.get("amount_untaxed", 0.5) * 0.8
            return
        if untaxed is None or total is None:
            return
        withholdings = sum(
            data.get(f, 0.0)
            for f in (
                "issqn_wh_value",
                "irpj_wh_value",
                "csll_wh_value",
                "pis_wh_value",
                "cofins_wh_value",
                "inss_wh_value",
            )
        )
        if abs(untaxed - withholdings - total) <= 0.01 or abs(untaxed - total) <= 0.01:
            confidence["amount_total"] = 1.0
            confidence["amount_untaxed"] = 1.0
