# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools.misc import formatLang


def _parse_float(raw, decimal_point="."):
    """Lê número digitado no formato brasileiro ou inglês.

    Com ponto e vírgula, o último é o decimal. Com um só separador, ele é de
    milhar quando não é o decimal do idioma e vem seguido de três dígitos;
    senão, é o decimal.
    """
    text = (raw or "").strip().replace(" ", "").replace("R$", "")
    if not text:
        return None
    if "," in text and "." in text:
        dec = "," if text.rfind(",") > text.rfind(".") else "."
    elif "," in text or "." in text:
        sep = "," if "," in text else "."
        parts = text.split(sep)
        if len(parts) > 2 or (len(parts[-1]) == 3 and sep != decimal_point):
            dec = None
        else:
            dec = sep
    else:
        dec = None
    if dec:
        thousands = "." if dec == "," else ","
        text = text.replace(thousands, "").replace(dec, ".")
    else:
        text = text.replace(",", "").replace(".", "")
    return float(text)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _rfq_portal_format_float(self, value, dp):
        """Número no formato do idioma do visitante (ex.: 2.725,00)."""
        if not value:
            return ""
        return formatLang(self.env, value, dp=dp)

    def _rfq_portal_decimal_point(self):
        lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US")
        return lang.decimal_point or "."

    def _rfq_portal_can_answer(self):
        """O fornecedor pode responder enquanto a rodada está em cotação, a
        cotação não foi confirmada e o prazo de resposta não passou."""
        self.ensure_one()
        rfq_round = self.rfq_round_id
        if not rfq_round or rfq_round.state != "quoting":
            return False
        if self.state not in ("draft", "sent"):
            return False
        deadline = rfq_round.date_deadline
        return not deadline or fields.Date.context_today(self) <= deadline

    def _rfq_portal_lines(self):
        self.ensure_one()
        return self.order_line.filtered("rfq_round_line_id")

    def _rfq_portal_line_fields(self):
        """Campos que o fornecedor preenche por item no portal.

        Cada campo: chave, rótulo, tipo (float, int, text, date, selection,
        bool), obrigatório, ``get(pol)`` com o valor atual e
        ``apply(pol, raw, vals)`` que valida o texto recebido e acumula em
        ``vals`` o que será gravado na linha. ``apply`` levanta ``ValueError``
        com a mensagem para o fornecedor. Módulos podem acrescentar campos.
        """
        return [
            {
                "key": "price_unit",
                "label": _("Unit Price"),
                "type": "float",
                "required": True,
                "get": lambda pol: self._rfq_portal_format_float(
                    pol.price_unit, "Product Price"
                ),
                "apply": self._rfq_portal_apply_price,
            },
            {
                "key": "delay",
                "label": _("Lead Time (days)"),
                "type": "int",
                "required": False,
                "get": lambda pol: (
                    max((pol.date_planned - pol.order_id.date_order).days, 0)
                    if pol.price_unit and pol.date_planned and pol.order_id.date_order
                    else ""
                ),
                "apply": self._rfq_portal_apply_delay,
            },
            {
                "key": "note",
                "label": _("Notes"),
                "type": "text",
                "required": False,
                "get": lambda pol: "",
                "apply": lambda pol, raw, vals: None,
            },
        ]

    def _rfq_portal_apply_price(self, pol, raw, vals):
        try:
            price = _parse_float(raw, self._rfq_portal_decimal_point())
        except ValueError as err:
            raise ValueError(_("Invalid price.")) from err
        if price is None:
            return
        if price < 0:
            raise ValueError(_("The price cannot be negative."))
        vals["price_unit"] = price

    def _rfq_portal_apply_delay(self, pol, raw, vals):
        try:
            days = _parse_float(raw, self._rfq_portal_decimal_point())
        except ValueError as err:
            raise ValueError(_("Invalid lead time.")) from err
        if days is None:
            return
        if days < 0:
            raise ValueError(_("The lead time cannot be negative."))
        base = pol.order_id.date_order or fields.Datetime.now()
        vals["date_planned"] = base + timedelta(days=int(days))

    def _rfq_portal_submit(self, post):
        """Valida e grava a resposta do fornecedor.

        ``post`` traz os campos como ``<chave>_<id da linha>``. Devolve um
        dicionário de erros (vazio quando a resposta foi gravada). Ou grava
        tudo, ou nada.
        """
        self.ensure_one()
        if not self._rfq_portal_can_answer():
            return {"_global": _("This quotation can no longer be answered.")}
        line_fields = self._rfq_portal_line_fields()
        errors, updates = {}, []
        for pol in self._rfq_portal_lines():
            vals, raw_values = {}, {}
            for field in line_fields:
                name = f"{field['key']}_{pol.id}"
                raw = post.get(name)
                raw_values[field["key"]] = raw
                if field["required"] and not (raw or "").strip():
                    if any(
                        (post.get(f"{f['key']}_{pol.id}") or "").strip()
                        for f in line_fields
                        if f["key"] != field["key"]
                    ):
                        errors[name] = _("Required.")
                    continue
                try:
                    field["apply"](pol, raw, vals)
                except ValueError as err:
                    errors[name] = str(err)
            # Só conta como respondida a linha com preço; os demais campos
            # (inclusive caixas desmarcadas) acompanham o preço.
            if "price_unit" in vals:
                updates.append((pol, vals, raw_values))
        if errors:
            return errors
        if not updates:
            return {"_global": _("Fill in at least one price.")}
        responses = []
        for pol, vals, raw_values in updates:
            pol.write(vals)
            responses.append(self._rfq_portal_prepare_response(pol, raw_values))
        self.env["purchase.rfq.round.response"].create(responses)
        self._rfq_portal_after_submit(len(updates))
        return {}

    def _rfq_portal_prepare_response(self, pol, raw_values):
        delay = 0
        if pol.date_planned and self.date_order:
            delay = max((pol.date_planned - self.date_order).days, 0)
        return {
            "round_id": self.rfq_round_id.id,
            "round_line_id": pol.rfq_round_line_id.id,
            "order_id": self.id,
            "order_line_id": pol.id,
            "partner_id": self.partner_id.id,
            "product_id": pol.product_id.id,
            "price_unit": pol.price_unit,
            "delay": delay,
            "note": (raw_values.get("note") or "").strip() or False,
            "source": "portal",
        }

    def _rfq_portal_after_submit(self, count):
        body = Markup("<p>%s</p>") % _(
            "%(vendor)s answered %(count)s items through the portal.",
            vendor=self.partner_id.display_name,
            count=count,
        )
        self.message_post(body=body, author_id=self.partner_id.id)
        self.rfq_round_id.message_post(
            body=Markup("<p>%s</p>")
            % _(
                "%(vendor)s answered %(order)s through the portal.",
                vendor=self.partner_id.display_name,
                order=self.name,
            )
        )
