# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Corrige o código do ASO demissional (RS-30).

O CSV original trazia o demissional com o código 8. O campo ``tpExameOcup`` do
S-2220 usa a série 0, 1, 2, 3, 4 e 9, e o demissional é o 9: um evento gerado
com 8 é rejeitado. Esta migração aponta quem já usava o registro antigo para o
novo e remove o obsoleto.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'l10n_br_esocial' AND name = 'tipo_aso_8'
        """
    )
    antigo = cr.fetchone()
    if not antigo:
        return
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'l10n_br_esocial' AND name = 'tipo_aso_9'
        """
    )
    novo = cr.fetchone()
    if not novo:
        _logger.warning(
            "eSocial: tipo_aso_9 ainda não existe; o tipo_aso_8 foi mantido."
        )
        return
    antigo_id, novo_id = antigo[0], novo[0]
    cr.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE column_name LIKE '%%tipo_aso_id'
        """
    )
    for table, column in cr.fetchall():
        cr.execute(
            f'UPDATE "{table}" SET "{column}" = %s WHERE "{column}" = %s',
            (novo_id, antigo_id),
        )
    cr.execute("DELETE FROM l10n_br_esocial_tipo_aso WHERE id = %s", (antigo_id,))
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'l10n_br_esocial' AND name = 'tipo_aso_8'
        """
    )
    _logger.info("eSocial: tipo de ASO demissional migrado do código 8 para o 9.")
