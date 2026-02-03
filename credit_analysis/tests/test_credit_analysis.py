# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCreditAnalysis(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CreditCompany = cls.env["credit.company"]
        cls.CreditAnalysis = cls.env["credit.analysis"]
        cls.CreditRestriction = cls.env["credit.restriction"]

    def test_create_company_valid_cnpj(self):
        """Test creating a company with a valid CNPJ."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        self.assertEqual(company.razao_social, "Test Company")
        self.assertTrue(company.active)

    def test_create_company_invalid_cnpj(self):
        """Test that creating a company with invalid CNPJ raises error."""
        with self.assertRaises(ValidationError):
            self.CreditCompany.create(
                {
                    "cnpj": "11.111.111/1111-11",
                    "razao_social": "Invalid Company",
                }
            )

    def test_cnpj_formatting(self):
        """Test CNPJ is formatted correctly."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11222333000181",
                "razao_social": "Test Company",
            }
        )
        self.assertEqual(company.cnpj_formatted, "11.222.333/0001-81")

    def test_score_validation(self):
        """Test that score must be between 0 and 1000."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 500,
            }
        )
        self.assertEqual(analysis.score, 500)

        with self.assertRaises(ValidationError):
            analysis.score = 1500

    def test_risk_level_computation(self):
        """Test risk level is computed correctly based on score."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 100,
            }
        )
        self.assertEqual(analysis.risk_level, "very_high")

        analysis.score = 300
        self.assertEqual(analysis.risk_level, "high")

        analysis.score = 500
        self.assertEqual(analysis.risk_level, "medium")

        analysis.score = 700
        self.assertEqual(analysis.risk_level, "low")

        analysis.score = 900
        self.assertEqual(analysis.risk_level, "very_low")

    def test_recommendation_computation(self):
        """Test recommendation is computed correctly."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        # High score without restrictions -> approved
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 800,
            }
        )
        self.assertEqual(analysis.recommendation, "approved")

        # Medium score -> caution
        analysis.score = 500
        self.assertEqual(analysis.recommendation, "caution")

        # Low score -> rejected
        analysis.score = 200
        self.assertEqual(analysis.recommendation, "rejected")

    def test_workflow_states(self):
        """Test workflow state transitions."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 500,
            }
        )
        self.assertEqual(analysis.state, "draft")

        analysis.action_confirm()
        self.assertEqual(analysis.state, "done")
        self.assertTrue(analysis.date_done)

        analysis.action_cancel()
        self.assertEqual(analysis.state, "cancelled")

        analysis.action_draft()
        self.assertEqual(analysis.state, "draft")

    def test_restriction_totals(self):
        """Test restriction totals are computed correctly."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 500,
            }
        )

        # Create restrictions
        self.CreditRestriction.create(
            {
                "analysis_id": analysis.id,
                "type": "negativacao",
                "value": 1000,
            }
        )
        self.CreditRestriction.create(
            {
                "analysis_id": analysis.id,
                "type": "negativacao",
                "value": 2000,
            }
        )
        self.CreditRestriction.create(
            {
                "analysis_id": analysis.id,
                "type": "protesto",
                "value": 500,
            }
        )

        self.assertEqual(analysis.total_negativacoes, 2)
        self.assertEqual(analysis.total_negativacoes_value, 3000)
        self.assertEqual(analysis.total_protestos, 1)
        self.assertEqual(analysis.total_protestos_value, 500)
        self.assertTrue(analysis.has_restricoes)
        self.assertEqual(analysis.total_restricoes_value, 3500)

    def test_tempo_mercado_computation(self):
        """Test tempo de mercado is computed from data_fundacao."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
                "data_fundacao": "2020-01-01",
            }
        )
        # tempo_mercado should be approximately 6 years
        self.assertGreaterEqual(company.tempo_mercado, 5)

    def test_duplicate_analysis(self):
        """Test duplicating an analysis creates a new draft."""
        company = self.CreditCompany.create(
            {
                "cnpj": "11.222.333/0001-81",
                "razao_social": "Test Company",
            }
        )
        analysis = self.CreditAnalysis.create(
            {
                "company_id": company.id,
                "score": 500,
            }
        )
        analysis.action_confirm()

        new_analysis = analysis.copy()
        self.assertEqual(new_analysis.state, "draft")
        self.assertEqual(new_analysis.company_id, company)
        self.assertEqual(new_analysis.score, 500)
        self.assertNotEqual(new_analysis.name, analysis.name)
