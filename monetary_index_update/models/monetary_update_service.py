from datetime import date
from typing import List, Optional, Tuple

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MonetaryUpdateService(models.AbstractModel):
    _name = "monetary.update.service"
    _description = "Monetary Update Service"
    _fields_to_track = []

    last_monetary_update_date = fields.Date(string="Last Monetary Update Date")

    @api.model
    def get_rate(
        self, index_code: str, target_date: date, policy: str = "exact"
    ) -> Optional[float]:
        """
        Get rate for a specific date.

        :param index_code: Code of the monetary index
        :param target_date: Target date
        :param policy: 'exact' or 'use_last_available'
        :return: Rate value or None
        """
        index = self._get_index_by_code(index_code)
        if not index:
            raise UserError(_("Index with code '%s' not found!") % index_code)

        domain = [
            ("index_id", "=", index.id),
            ("date", "=", target_date),
        ]
        rate = self.env["monetary.index.rate"].search(domain, limit=1)

        if rate:
            return rate.value

        if policy == "use_last_available":
            domain = [
                ("index_id", "=", index.id),
                ("date", "<=", target_date),
            ]
            rate = self.env["monetary.index.rate"].search(
                domain, order="date desc", limit=1
            )
            if rate:
                return rate.value

        return None

    @api.model
    def get_series(
        self, index_code: str, start_date: date, end_date: date
    ) -> List[Tuple[date, float]]:
        """
        Get series of rates between two dates.

        :param index_code: Code of the monetary index
        :param start_date: Start date
        :param end_date: End date
        :return: List of tuples (date, value)
        """
        index = self._get_index_by_code(index_code)
        if not index:
            raise UserError(_("Index with code '%s' not found!") % index_code)

        domain = [
            ("index_id", "=", index.id),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
        ]
        rates = self.env["monetary.index.rate"].search(domain, order="date asc")

        return [(rate.date, rate.value) for rate in rates]

    @api.model
    def compute_factor(
        self,
        index_code: str,
        start_date: date,
        end_date: date,
        mode: str = "compound",
        missing: str = "error",
    ) -> float:
        """
        Compute accumulated factor between two dates.

        :param index_code: Code of the monetary index
        :param start_date: Start date
        :param end_date: End date
        :param mode: 'compound' or 'simple'
        :param missing: 'error', 'use_last_available', or 'skip'
        :return: Accumulated factor
        """
        if mode not in ("compound", "simple"):
            raise UserError(_("Invalid mode: %s. Use 'compound' or 'simple'.") % mode)

        if missing not in ("error", "use_last_available", "skip"):
            raise UserError(
                _(
                    "Invalid missing policy: %s. Use 'error', 'use_last_available', or 'skip'."
                )
                % missing
            )

        series = self.get_series(index_code, start_date, end_date)

        if not series and missing == "error":
            raise UserError(
                _("No rates found for index '%s' between %s and %s!")
                % (index_code, start_date, end_date)
            )

        if mode == "compound":
            factor = 1.0
            for x, value in series:  # noqa: B007
                factor *= 1.0 + value / 100.0
            return factor
        else:  # simple
            total = sum(value for x, value in series)  # noqa: B007
            return 1.0 + total / 100.0

    @api.model
    def compute_updated_amount(
        self, index_code: str, amount: float, start_date: date, end_date: date, **kwargs
    ) -> float:
        """
        Update an amount using the accumulated factor.

        :param index_code: Code of the monetary index
        :param amount: Original amount
        :param start_date: Start date
        :param end_date: End date
        :param kwargs: Additional arguments passed to compute_factor
        :return: Updated amount
        """
        factor = self.compute_factor(index_code, start_date, end_date, **kwargs)
        return amount * factor

    @api.model
    def compute_factor_with_strategy(
        self,
        index_code: str,
        start_date: date,
        end_date: date,
        strategy_code: str,
        **kwargs,
    ) -> float:
        """
        Compute factor using a registered strategy.

        :param index_code: Code of the monetary index
        :param start_date: Start date
        :param end_date: End date
        :param strategy_code: Code of the strategy to use
        :param kwargs: Additional arguments for the strategy
        :return: Computed factor
        """
        strategy_registry = self.env["monetary.update.strategy"]
        strategy = strategy_registry.get_strategy(strategy_code)

        if not strategy:
            raise UserError(_("Strategy '%s' not found!") % strategy_code)

        return strategy(self, index_code, start_date, end_date, **kwargs)

    @api.model
    def _get_index_by_code(self, code: str):
        """Helper method to get index by code."""
        return self.env["monetary.index"].search([("code", "=ilike", code)], limit=1)

    @api.model
    def monetary_update_fields_by_index_wizard(self, res_id):
        model = self.env["ir.model"].search([("model", "=", self._name)])
        if not model:
            raise UserError(_("Model '%s' not found!") % self._name)

        record = self.env[model.model].browse(res_id[0])
        if not record:
            raise UserError(_("Record '%s' not found!") % res_id[0])

        start_date = record.last_monetary_update_date

        return {
            "type": "ir.actions.act_window",
            "name": "Monetary Update by Index Wizard",
            "res_model": "monetary.update.by.index.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model_id": model.id,
                "default_res_id": res_id[0],
                "default_start_date": start_date,
                "field_names": self._fields_to_track,
            },
        }
