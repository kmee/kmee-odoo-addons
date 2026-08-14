# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Fixtures compartilhadas pelos testes de registro de ponto."""

from datetime import datetime

from odoo.tests.common import TransactionCase


class PontoCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.rep = cls.env["l10n_br.hr.rep"].create(
            {
                "name": "REP-C Portaria",
                "tipo": "rep_c",
                "numero_fabricacao": "12345678901234567",
                "cnpj_cpf": "12.345.678/0001-95",
                "company_id": cls.company.id,
                "atestado_date_start": "2020-01-01",
                "atestado_date_end": "2099-12-31",
            }
        )
        # O CPF do funcionário mora no endereço particular (related ao ``vat``
        # do partner) no l10n_br_hr; criar o partner reproduz o cadastro real.
        cls.partner_maria = cls.env["res.partner"].create(
            {
                "name": "Maria da Silva",
                "vat": "434.612.928-50",
                "country_id": cls.env.ref("base.br").id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Maria da Silva",
                "company_id": cls.company.id,
                "address_home_id": cls.partner_maria.id,
                "pis_pasep": "120.45678.90-5",
                "tz": "America/Sao_Paulo",
            }
        )

    @classmethod
    def _criar_marcacao(cls, nsr, momento, employee=None, **extra):
        """Cria marcação original (o caminho normal passa pelo helper)."""
        vals = {
            "nsr": nsr,
            "rep_id": cls.rep.id,
            "company_id": cls.company.id,
            "datetime_marcacao": momento,
            "origem": "rep_c",
        }
        employee = cls.employee if employee is None else employee
        if employee:
            vals["employee_id"] = employee.id
        vals.update(extra)
        return cls.env["l10n_br.hr.marcacao"]._criar_marcacoes([vals])

    @staticmethod
    def _utc(ano, mes, dia, hora, minuto=0):
        """Datetime naive em UTC, como o ORM armazena."""
        return datetime(ano, mes, dia, hora, minuto)
