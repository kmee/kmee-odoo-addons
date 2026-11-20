# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockBuffer(models.Model):
    _inherit = "stock.buffer"

    def _get_rfq_dlt(self, dlt_interval=None):
        """Conta uma vez cada necessidade cotada com vários fornecedores.

        O ddmrp soma todas as linhas de cotação ligadas ao buffer. Numa rodada
        (ou num grupo de Alternativas do core) a mesma quantidade aparece uma
        vez por fornecedor. Aqui fica uma linha por item da rodada, ou por
        produto do grupo de Alternativas: a vencedora, se houver, senão a de
        maior quantidade. Linhas não são desligadas do buffer (o ddmrp as
        religa a cada gravação); só deixam de ser contadas.

        A escolha é feita sobre todas as linhas, antes do corte pela janela
        do DLT: fornecedores com prazos diferentes caem em janelas diferentes,
        e deduplicar dentro de cada janela contaria a mesma necessidade duas
        vezes.
        """
        lines = super()._get_rfq_dlt(dlt_interval=dlt_interval)
        if not lines:
            return lines
        if dlt_interval is not None:
            all_lines = super()._get_rfq_dlt(dlt_interval=None)
        else:
            all_lines = lines
        return lines & self._ddmrp_dedup_rfq_lines(all_lines)

    def _ddmrp_dedup_rfq_lines(self, lines):
        groups = {}
        kept = lines.browse()
        for line in lines:
            key = line._ddmrp_dedup_key()
            if key is None:
                kept |= line
            else:
                groups.setdefault(key, lines.browse())
                groups[key] |= line
        for group_lines in groups.values():
            kept |= group_lines._ddmrp_dedup_pick()
        return kept

    def _get_open_purchase_request_lines(self):
        """Requisições já em cotação numa rodada saem da conta da requisição.

        Quando a rodada cria as cotações, a quantidade passa a ser contada
        pelas linhas de cotação; contar também a requisição dobraria o valor.
        """
        lines = super()._get_open_purchase_request_lines()
        return lines.filtered(lambda line: line.rfq_round_id.state != "quoting")
