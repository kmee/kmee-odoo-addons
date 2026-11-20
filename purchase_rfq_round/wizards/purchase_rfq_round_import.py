# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import logging
import re
import unicodedata
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.utils import column_index_from_string, get_column_letter
except ImportError:  # pragma: no cover
    _logger.debug("openpyxl not available")


def _normalize(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore")
    text = re.sub(r"[^a-z0-9%]+", " ", text.decode().lower())
    return " ".join(text.split())


def _to_float(value):
    if value in (None, ""):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


class PurchaseRfqRoundImport(models.TransientModel):
    _name = "purchase.rfq.round.import"
    _description = "Import Quotation Round Responses"

    round_id = fields.Many2one("purchase.rfq.round", required=True)
    order_id = fields.Many2one(
        "purchase.order",
        string="Quotation",
        domain="[('rfq_round_id', '=', round_id), ('state', '!=', 'cancel')]",
        help="Obrigatório quando a planilha não tem a coluna ID (planilha "
        "própria do fornecedor): os itens são localizados pelo código ou nome.",
    )
    file = fields.Binary(required=True)
    file_name = fields.Char()
    state = fields.Selection(
        [("upload", "Upload"), ("mapping", "Mapping")], default="upload"
    )
    header_row = fields.Integer(help="Linha do cabeçalho na planilha (1 = primeira).")
    column_ids = fields.One2many(
        "purchase.rfq.round.import.column", "wizard_id", string="Columns"
    )
    result = fields.Text(readonly=True)

    # ------------------------------------------------------------------
    # Colunas
    # ------------------------------------------------------------------

    @api.model
    def _get_import_columns(self):
        """Colunas reconhecidas. ``synonyms`` são comparados sem acento e sem
        caixa; o primeiro cabeçalho que começa com um sinônimo vence.
        ``apply(wizard, po_line, value, vals)`` acumula em ``vals`` o que será
        gravado na linha da cotação."""
        return [
            {"key": "line_id", "label": "ID", "synonyms": ["id"]},
            {
                "key": "default_code",
                "label": _("Code"),
                "synonyms": ["codigo", "code", "cod", "referencia", "ref", "sku"],
            },
            {
                "key": "product",
                "label": _("Product"),
                "synonyms": ["produto", "product", "descricao", "item"],
            },
            {
                "key": "price_unit",
                "label": _("Unit Price"),
                "synonyms": [
                    "preco unitario",
                    "unit price",
                    "valor unitario",
                    "vlr unit",
                    "vl unit",
                    "preco un",
                    "preco",
                    "price",
                    "valor",
                ],
                "required": True,
                "apply": self._apply_price_unit,
            },
            {
                "key": "delay",
                "label": _("Lead Time (days)"),
                "synonyms": [
                    "prazo de entrega",
                    "delivery lead time",
                    "lead time",
                    "prazo",
                    "dias",
                ],
                "apply": self._apply_delay,
            },
            {
                "key": "note",
                "label": _("Notes"),
                "synonyms": ["observacao", "observacoes", "notes", "note", "obs"],
            },
        ]

    @api.model
    def _apply_price_unit(self, po_line, value, vals):
        price = _to_float(value)
        if price is not None and price >= 0.0:
            vals["price_unit"] = price

    @api.model
    def _apply_delay(self, po_line, value, vals):
        days = _to_float(value)
        if days is not None and days >= 0.0:
            base = po_line.order_id.date_order or fields.Datetime.now()
            vals["date_planned"] = base + timedelta(days=int(days))

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def _load_rows(self):
        self.ensure_one()
        try:
            book = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.file)), data_only=True, read_only=True
            )
        except Exception as err:
            raise UserError(_("Could not read the spreadsheet: %s", err)) from err
        sheet = book.worksheets[0]
        return [list(row) for row in sheet.iter_rows(values_only=True)]

    def _detect(self, rows):
        """Acha a linha de cabeçalho e o mapeamento de colunas."""
        columns = self._get_import_columns()
        for index, row in enumerate(rows[:30]):
            headers = [_normalize(cell) for cell in row]
            mapping = {}
            for column in columns:
                for synonym in column["synonyms"]:
                    found = next(
                        (
                            pos
                            for pos, head in enumerate(headers)
                            if head
                            and pos not in mapping.values()
                            and (head == synonym or head.startswith(synonym + " "))
                        ),
                        None,
                    )
                    if found is None:
                        found = next(
                            (
                                pos
                                for pos, head in enumerate(headers)
                                if head
                                and pos not in mapping.values()
                                and head.startswith(synonym)
                            ),
                            None,
                        )
                    if found is not None:
                        mapping[column["key"]] = found
                        break
            if "price_unit" in mapping and (
                {"line_id", "default_code", "product"} & mapping.keys()
            ):
                return index, mapping
        return None, {}

    def action_analyze(self):
        self.ensure_one()
        rows = self._load_rows()
        header_index, mapping = self._detect(rows)
        columns = self._get_import_columns()
        self.column_ids = [Command.clear()] + [
            Command.create(
                {
                    "key": column["key"],
                    "label": column["label"],
                    "column": (
                        get_column_letter(mapping[column["key"]] + 1)
                        if column["key"] in mapping
                        else False
                    ),
                }
            )
            for column in columns
        ]
        self.header_row = header_index + 1 if header_index is not None else 1
        self.state = "mapping"
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Responses"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_mapping(self):
        mapping = {}
        for col in self.column_ids.filtered("column"):
            try:
                mapping[col.key] = (
                    column_index_from_string(col.column.strip().upper()) - 1
                )
            except ValueError as err:
                raise UserError(_("Invalid column: %s", col.column)) from err
        if "price_unit" not in mapping:
            raise UserError(_("Map the unit price column."))
        if not ({"line_id", "default_code", "product"} & mapping.keys()):
            raise UserError(_("Map the ID, code or product column."))
        if "line_id" not in mapping and not self.order_id:
            raise UserError(
                _("Without the ID column, choose the quotation of this vendor.")
            )
        return mapping

    # ------------------------------------------------------------------
    # Importação
    # ------------------------------------------------------------------

    def _find_po_line(self, row, mapping, round_lines):
        def cell(key):
            pos = mapping.get(key)
            return row[pos] if pos is not None and pos < len(row) else None

        line_id = _to_float(cell("line_id")) if "line_id" in mapping else None
        if line_id:
            po_line = self.env["purchase.order.line"].browse(int(line_id)).exists()
            if po_line and po_line.rfq_round_line_id in round_lines:
                if not self.order_id or po_line.order_id == self.order_id:
                    return po_line
            return None
        if not self.order_id:
            return None
        code = _normalize(cell("default_code"))
        name = _normalize(cell("product"))
        for po_line in self.order_id.order_line.filtered("rfq_round_line_id"):
            product = po_line.product_id
            if code and _normalize(product.default_code) == code:
                return po_line
            if name and name in (
                _normalize(product.name),
                _normalize(product.display_name),
            ):
                return po_line
        return None

    def action_import(self):
        self.ensure_one()
        rows = self._load_rows()
        mapping = self._get_mapping()
        columns = {c["key"]: c for c in self._get_import_columns()}
        round_lines = self.round_id.line_ids
        imported, skipped = 0, []
        responses = []
        start = self.header_row or 1
        for number, row in enumerate(rows[start:], start + 1):
            if not any(cell not in (None, "") for cell in row):
                continue
            po_line = self._find_po_line(row, mapping, round_lines)
            if not po_line:
                skipped.append(_("row %s: item not found in the round", number))
                continue
            vals, raw = {}, {}
            for key, pos in mapping.items():
                value = row[pos] if pos < len(row) else None
                raw[key] = (
                    value if not hasattr(value, "isoformat") else value.isoformat()
                )
                apply = columns.get(key, {}).get("apply")
                if apply and value not in (None, ""):
                    apply(po_line, value, vals)
            if "price_unit" not in vals:
                skipped.append(_("row %s: no valid price", number))
                continue
            po_line.write(vals)
            responses.append(self._prepare_response(po_line, raw, vals))
            imported += 1
        self.env["purchase.rfq.round.response"].create(responses)
        lines = [
            _(
                "%(count)s items imported from %(file)s.",
                count=imported,
                file=self.file_name or "file",
            )
        ]
        lines += skipped[:50]
        if len(skipped) > 50:
            lines.append(_("... and %s more rows ignored.", len(skipped) - 50))
        self.result = "\n".join(lines)
        self.round_id.message_post(body="<br/>".join(lines))
        return self._reopen()

    def _prepare_response(self, po_line, raw, vals):
        delay = _to_float(raw.get("delay"))
        return {
            "round_id": self.round_id.id,
            "round_line_id": po_line.rfq_round_line_id.id,
            "order_id": po_line.order_id.id,
            "order_line_id": po_line.id,
            "partner_id": po_line.order_id.partner_id.id,
            "product_id": po_line.product_id.id,
            "price_unit": vals.get("price_unit", 0.0),
            "delay": int(delay) if delay is not None else 0,
            "note": str(raw["note"]) if raw.get("note") not in (None, "") else False,
            "source": "import",
            "file_name": self.file_name,
            "raw_values": raw,
        }


class PurchaseRfqRoundImportColumn(models.TransientModel):
    _name = "purchase.rfq.round.import.column"
    _description = "Quotation Round Import Column Mapping"

    wizard_id = fields.Many2one("purchase.rfq.round.import", ondelete="cascade")
    key = fields.Char(required=True, readonly=True)
    label = fields.Char(readonly=True)
    column = fields.Char(help="Letra da coluna na planilha (A, B, C...).")
