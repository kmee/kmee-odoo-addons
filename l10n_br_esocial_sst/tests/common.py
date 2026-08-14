# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon

_logger = logging.getLogger(__name__)

try:
    import esociallib  # noqa: F401

    HAS_ESOCIALLIB = True
except ImportError:  # pragma: no cover
    HAS_ESOCIALLIB = False
    _logger.warning("esociallib não instalada — testes de XML serão pulados")


class EsocialSstCommon(SstCommon):
    """Cenário de SST pronto para gerar evento: empresa, risco, EPI e ASO."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hoje = fields.Date.context_today(cls.env["l10n_br.sst.ca"])
        cls.company.write(
            {
                "l10n_br_esocial_tp_amb": "2",
                "l10n_br_esocial_processo_emissao": "1",
            }
        )
        cls.employee.write(
            {
                "l10n_br_esocial_matricula": "MAT001",
                "l10n_br_esocial_categoria_id": cls.env.ref(
                    "l10n_br_esocial.cat_trab_101"
                ).id,
            }
        )
        cls.laudo.action_vigente()
        cls.ca = cls.env["l10n_br.sst.ca"].create(
            {
                "numero": "31000",
                "descricao_epi": "Protetor auricular tipo concha",
                "validade": cls.hoje + relativedelta(years=1),
                "risco_neutralizado_ids": [(6, 0, [cls.risco.id])],
            }
        )
        cls.produto = cls.env["product.product"].create(
            {
                "name": "Protetor Auricular",
                "type": "consu",
                "is_personal_equipment": True,
                "is_ppe": True,
                "l10n_br_sst_ca_id": cls.ca.id,
            }
        )

    @classmethod
    def _entrega_epi(cls, data=None):
        request = cls.env["hr.personal.equipment.request"].create(
            {
                "employee_id": cls.employee.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.produto.id,
                            "quantity": 1,
                            "start_date": data or cls.hoje,
                            "l10n_br_sst_ca_id": cls.ca.id,
                        },
                    )
                ],
            }
        )
        request.accept_request()
        request.line_ids.validate_allocation()
        return request.line_ids
