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

    BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

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
        self,
        date_from: Optional[fields.Date],
        date_to: Optional[fields.Date],
        sgs_code: str = "4390",
    ) -> List[Dict[str, str]]:
        params = self._build_bcb_params(date_from, date_to)
        url = self.BCB_SGS_URL.format(code=sgs_code)
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            _logger.exception("Failed to fetch SGS series %s from BCB.", sgs_code)
            raise UserError(
                _(
                    "Falha ao consultar a série %(code)s na API do Banco Central. "
                    "Tente novamente mais tarde."
                )
                % {"code": sgs_code}
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
                _logger.warning("Skipping invalid BCB entry: %s", item)
                continue
            rates.append((rate_date, value))
        return rates

    @api.model
    def update_rates(
        self,
        index,
        date_from: Optional[fields.Date] = None,
        date_to: Optional[fields.Date] = None,
        force: bool = False,
    ) -> Dict[str, int]:
        """Fetch the SGS series of the index from the BCB and store its rates."""
        index.ensure_one()
        if not index.bcb_sgs_code:
            raise UserError(
                _("O índice %(name)s não tem código de série do SGS.")
                % {"name": index.name}
            )
        payload = self._fetch_bcb_series(date_from, date_to, index.bcb_sgs_code)
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
    def update_selic_rates(
        self,
        date_from: Optional[fields.Date] = None,
        date_to: Optional[fields.Date] = None,
        force: bool = False,
    ) -> Dict[str, int]:
        return self.update_rates(
            self._get_selic_index(), date_from=date_from, date_to=date_to, force=force
        )

    @api.model
    def cron_update_rates(self) -> Dict[str, Dict[str, int]]:
        """Update every active index with an SGS code, from three months ago.

        Monthly series (IPCA, INPC, IGP-M) are published around the 10th of the
        following month and may be revised, so the last three months are fetched
        again on every run.
        """
        today = fields.Date.today()
        date_from = (today - relativedelta(months=3)).replace(day=1)
        result = {}
        for index in self.env["monetary.index"].search([("bcb_sgs_code", "!=", False)]):
            try:
                result[index.code] = self.update_rates(
                    index, date_from=date_from, date_to=today
                )
            except UserError as exc:
                _logger.warning("Index %s not updated: %s", index.code, exc)
        return result

    @api.model
    def cron_update_selic_rates(self) -> Dict[str, int]:
        """Kept for databases whose cron still calls the SELIC-only method."""
        today = fields.Date.today()
        date_from = (today - relativedelta(months=1)).replace(day=1)
        return self.update_selic_rates(date_from=date_from, date_to=today)
