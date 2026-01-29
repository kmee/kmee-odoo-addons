import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class MonetaryIndexProvider(models.AbstractModel):
    _name = "monetary.index.provider"
    _description = "Monetary Index Provider"

    BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados"

    @api.model
    def _get_selic_index(self):
        index = self.env["monetary.index"].search(
            [("code", "=ilike", "SELIC")], limit=1
        )
        if not index:
            raise UserError(_("Monetary index 'SELIC' not found."))
        return index

    @api.model
    def _build_bcb_params(
        self, date_from: Optional[fields.Date], date_to: Optional[fields.Date]
    ) -> Dict[str, str]:
        params = {"formato": "json"}
        if date_from:
            params["dataInicial"] = date_from.strftime("%d/%m/%Y")
        if date_to:
            params["dataFinal"] = date_to.strftime("%d/%m/%Y")
        return params

    @api.model
    def _fetch_bcb_series(
        self, date_from: Optional[fields.Date], date_to: Optional[fields.Date]
    ) -> List[Dict[str, str]]:
        params = self._build_bcb_params(date_from, date_to)
        try:
            response = requests.get(self.BCB_SELIC_URL, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            _logger.exception("Failed to fetch SELIC series from BCB.")
            raise UserError(
                _(
                    "Falha ao consultar a API do Banco Central. "
                    "Tente novamente mais tarde. Caso persista, "
                    "considere usar a API interna do Grupo AG Capital."
                )
            ) from exc
        if not isinstance(payload, list):
            raise UserError(_("Resposta inesperada da API do Banco Central."))
        return payload

    @api.model
    def _parse_bcb_payload(
        self, payload: Iterable[Dict[str, str]]
    ) -> List[Tuple[fields.Date, float]]:
        rates: List[Tuple[fields.Date, float]] = []
        for item in payload:
            try:
                rate_date = datetime.strptime(item.get("data"), "%d/%m/%Y").date()
                value = float(item.get("valor", "").replace(",", "."))
            except (TypeError, ValueError, AttributeError):
                _logger.warning("Skipping invalid SELIC entry: %s", item)
                continue
            rates.append((rate_date, value))
        return rates

    @api.model
    def update_selic_rates(
        self,
        date_from: Optional[fields.Date] = None,
        date_to: Optional[fields.Date] = None,
        force: bool = False,
    ) -> Dict[str, int]:
        index = self._get_selic_index()
        payload = self._fetch_bcb_series(date_from, date_to)
        rates = self._parse_bcb_payload(payload)

        created = updated = skipped = 0
        rate_model = self.env["monetary.index.rate"]
        for rate_date, value in rates:
            rate = rate_model.search(
                [("index_id", "=", index.id), ("date", "=", rate_date)],
                limit=1,
            )
            if rate:
                if force or float_compare(rate.value, value, precision_digits=6) != 0:
                    rate.write({"value": value, "source": "api", "note": "BCB"})
                    updated += 1
                else:
                    skipped += 1
                continue
            rate_model.create(
                {
                    "index_id": index.id,
                    "date": rate_date,
                    "value": value,
                    "source": "api",
                    "note": "BCB",
                }
            )
            created += 1
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(rates),
        }

    @api.model
    def cron_update_selic_rates(self) -> Dict[str, int]:
        today = fields.Date.today()
        date_from = (today - relativedelta(months=1)).replace(day=1)
        return self.update_selic_rates(date_from=date_from, date_to=today)
