# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundLine(models.Model):
    _inherit = "purchase.rfq.round.line"

    def _rfq_is_eligible(self, quote):
        """Resposta elegível para pontuar e vencer."""
        rfq_round = self.round_id
        if quote.rfq_validity_date and quote.rfq_validity_date < fields.Date.today():
            return False
        if rfq_round.require_approved and not (
            quote.rfq_vendor_approved and quote.rfq_spec_approved
        ):
            return False
        return True

    def _rfq_compute_scores(self):
        """Pontua as respostas de cada item (0 a 100).

        Preço: menor custo unitário / custo da resposta, na base da rodada.
        Prazo: menor prazo / prazo da resposta (prazo zero conta como 1 dia).
        A nota é a média ponderada pelos pesos da rodada.
        """
        for line in self:
            rfq_round = line.round_id
            quotes = line._answered_quotes()
            eligible = quotes.filtered(line._rfq_is_eligible)
            (line.quote_line_ids - eligible).write(
                {"rfq_score": 0.0, "rfq_eligible": False}
            )
            if not eligible:
                continue
            costs = {
                q.id: q._rfq_effective_unit_cost(rfq_round.price_basis)
                for q in eligible
            }
            leads = {q.id: max(q.rfq_lead_days, 1) for q in eligible}
            best_cost = min(costs.values())
            best_lead = min(leads.values())
            weight_total = (rfq_round.weight_price + rfq_round.weight_delay) or 1.0
            for quote in eligible:
                price_ratio = best_cost / costs[quote.id] if costs[quote.id] else 0.0
                lead_ratio = best_lead / leads[quote.id]
                score = (
                    100.0
                    * (
                        rfq_round.weight_price * price_ratio
                        + rfq_round.weight_delay * lead_ratio
                    )
                    / weight_total
                )
                quote.write({"rfq_score": score, "rfq_eligible": True})

    def _get_quote_sort_key(self, criterion):
        if criterion == "score":
            basis = self.round_id.price_basis
            return lambda pol: (-pol.rfq_score, pol._rfq_effective_unit_cost(basis))
        return super()._get_quote_sort_key(criterion)

    def _get_best_quote(self, criterion):
        if criterion != "score":
            return super()._get_best_quote(criterion)
        quotes = self._answered_quotes().filtered(
            lambda q: q.rfq_eligible and q.rfq_score > 0.0
        )
        if not quotes:
            return quotes
        return min(quotes, key=self._get_quote_sort_key("score"))
