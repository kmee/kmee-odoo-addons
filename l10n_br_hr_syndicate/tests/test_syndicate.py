# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Sindicato, Convenções Coletivas e Contribuições.

Cobertura:
  - CRUD de convenções coletivas
  - Piso salarial por cargo
  - Contribuição sindical (percentual, fixo, um dia)
  - Vínculo sindicato ↔ contrato (via OCA partner_union)
"""
from datetime import date

from odoo.tests.common import TransactionCase


class TestSyndicate(TransactionCase):
    """Testes de sindicato e convenções coletivas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_union = cls.env["res.partner"].create(
            {
                "name": "Sindicato dos Trabalhadores em TI",
                "union_entity_code": "STI001",
                "is_company": True,
            }
        )
        cls.job = cls.env["hr.job"].create({"name": "Desenvolvedor"})

    def test_create_collective_convention(self):
        """Cria convenção coletiva com campos obrigatórios."""
        convention = self.env["l10n.br.hr.collective.convention"].create(
            {
                "name": "CCT TI 2024/2025",
                "partner_union_id": self.partner_union.id,
                "date_start": date(2024, 5, 1),
                "date_end": date(2025, 4, 30),
                "dissidio_month": "5",
                "wage_floor": 3500.00,
            }
        )
        self.assertEqual(convention.partner_union_id, self.partner_union)
        self.assertEqual(convention.dissidio_month, "5")
        self.assertAlmostEqual(convention.wage_floor, 3500.00, places=2)

    def test_convention_wage_floor_by_job(self):
        """Piso salarial diferenciado por cargo."""
        convention = self.env["l10n.br.hr.collective.convention"].create(
            {
                "name": "CCT 2024",
                "partner_union_id": self.partner_union.id,
                "date_start": date(2024, 1, 1),
                "date_end": date(2024, 12, 31),
                "wage_floor": 2000.00,
            }
        )
        wage_floor = self.env["l10n.br.hr.convention.wage.floor"].create(
            {
                "convention_id": convention.id,
                "job_id": self.job.id,
                "wage_floor": 4500.00,
            }
        )
        self.assertEqual(wage_floor.convention_id, convention)
        self.assertAlmostEqual(wage_floor.wage_floor, 4500.00, places=2)

    def test_convention_contribution_rates(self):
        """Taxas de contribuição empregado e patronal."""
        convention = self.env["l10n.br.hr.collective.convention"].create(
            {
                "name": "CCT 2024",
                "partner_union_id": self.partner_union.id,
                "date_start": date(2024, 1, 1),
                "date_end": date(2024, 12, 31),
                "contribution_employee_pct": 1.5,
                "contribution_employer_pct": 3.0,
            }
        )
        self.assertAlmostEqual(convention.contribution_employee_pct, 1.5, places=2)
        self.assertAlmostEqual(convention.contribution_employer_pct, 3.0, places=2)

    def test_create_contribution_percent(self):
        """Contribuição sindical com método percentual."""
        contrib = self.env["l10n.br.hr.syndicate.contribution"].create(
            {
                "partner_union_id": self.partner_union.id,
                "year": 2024,
                "month": "3",
                "contribution_type": "assistencial",
                "calc_method": "percent",
                "percentage": 2.0,
            }
        )
        self.assertEqual(contrib.calc_method, "percent")
        self.assertAlmostEqual(contrib.percentage, 2.0, places=2)

    def test_create_contribution_fixed(self):
        """Contribuição sindical com valor fixo."""
        contrib = self.env["l10n.br.hr.syndicate.contribution"].create(
            {
                "partner_union_id": self.partner_union.id,
                "year": 2024,
                "month": "3",
                "contribution_type": "sindical",
                "calc_method": "fixed",
                "fixed_amount": 150.00,
            }
        )
        self.assertEqual(contrib.calc_method, "fixed")
        self.assertAlmostEqual(contrib.fixed_amount, 150.00, places=2)

    def test_create_contribution_one_day(self):
        """Contribuição sindical de um dia de salário."""
        contrib = self.env["l10n.br.hr.syndicate.contribution"].create(
            {
                "partner_union_id": self.partner_union.id,
                "year": 2024,
                "month": "3",
                "contribution_type": "sindical",
                "calc_method": "one_day",
            }
        )
        self.assertEqual(contrib.calc_method, "one_day")

    def test_contribution_types(self):
        """Todos os tipos de contribuição são válidos."""
        for ctype in ("assistencial", "confederativa", "sindical"):
            contrib = self.env["l10n.br.hr.syndicate.contribution"].create(
                {
                    "partner_union_id": self.partner_union.id,
                    "year": 2024,
                    "month": "1",
                    "contribution_type": ctype,
                    "calc_method": "percent",
                    "percentage": 1.0,
                }
            )
            self.assertEqual(contrib.contribution_type, ctype)

    def test_convention_cascade_delete(self):
        """Deletar convenção remove pisos por cargo."""
        convention = self.env["l10n.br.hr.collective.convention"].create(
            {
                "name": "CCT Temp",
                "partner_union_id": self.partner_union.id,
                "date_start": date(2024, 1, 1),
                "date_end": date(2024, 12, 31),
            }
        )
        self.env["l10n.br.hr.convention.wage.floor"].create(
            {
                "convention_id": convention.id,
                "job_id": self.job.id,
                "wage_floor": 3000.00,
            }
        )
        floor_count_before = self.env["l10n.br.hr.convention.wage.floor"].search_count(
            [("job_id", "=", self.job.id)]
        )
        convention.unlink()
        floor_count_after = self.env["l10n.br.hr.convention.wage.floor"].search_count(
            [("job_id", "=", self.job.id)]
        )
        self.assertLess(floor_count_after, floor_count_before)
