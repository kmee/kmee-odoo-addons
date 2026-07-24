# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Validações do cadastro de funcionário brasileiro.

Cobertura:
  - Validação de CPF (algoritmo + casos especiais)
  - Validação de PIS/PASEP
  - Unicidade de CPF e PIS
  - Formatação automática
  - Campos obrigatórios por tipo de contrato
"""
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestCPFValidacao(TransactionCase):
    """Testes de validação do CPF."""

    def setUp(self):
        super().setUp()
        self.model = self.env["hr.employee"]
        self.company = self.env.ref("base.main_company")

    def _make(self, cpf, name="Teste CPF"):
        return self.model.create(
            {
                "name": name,
                "l10n_br_cpf": cpf,
                "company_id": self.company.id,
            }
        )

    # ── CPFs válidos ──────────────────────────────────────────────
    def test_cpf_valido_com_pontuacao(self):
        """CPF válido com pontos e traço deve ser aceito."""
        emp = self._make("123.456.789-09")
        self.assertEqual(emp.l10n_br_cpf, "123.456.789-09")

    def test_cpf_valido_apenas_numeros(self):
        """CPF válido apenas com números deve ser formatado e aceito."""
        emp = self._make("12345678909")
        # Deve formatar automaticamente
        self.assertEqual(emp.l10n_br_cpf, "123.456.789-09")

    def test_cpf_valido_outro(self):
        """Segundo CPF válido — garantir que o algoritmo funciona em casos distintos."""
        emp = self._make("529.982.247-25")
        self.assertTrue(emp.id)

    # ── CPFs inválidos ────────────────────────────────────────────
    def test_cpf_invalido_digito_verificador_errado(self):
        """CPF com dígito verificador errado deve ser rejeitado."""
        with self.assertRaises(
            (UserError, ValidationError), msg="CPF inválido deve lançar erro"
        ):
            self._make("123.456.789-00")

    def test_cpf_invalido_todos_iguais_111(self):
        """CPF com todos os dígitos iguais (111.111.111-11) é inválido."""
        with self.assertRaises((UserError, ValidationError)):
            self._make("111.111.111-11")

    def test_cpf_invalido_todos_iguais_000(self):
        """CPF 000.000.000-00 é inválido."""
        with self.assertRaises((UserError, ValidationError)):
            self._make("000.000.000-00")

    def test_cpf_invalido_sequencias_especiais(self):
        """Todas as sequências de dígitos repetidos são inválidas."""
        cpfs_invalidos = [
            "111.111.111-11",
            "222.222.222-22",
            "333.333.333-33",
            "444.444.444-44",
            "555.555.555-55",
            "666.666.666-66",
            "777.777.777-77",
            "888.888.888-88",
            "999.999.999-99",
        ]
        for cpf in cpfs_invalidos:
            with self.assertRaises(
                (UserError, ValidationError), msg=f"CPF {cpf} deve ser rejeitado"
            ):
                self._make(cpf)

    def test_cpf_invalido_tamanho_errado(self):
        """CPF com menos de 11 dígitos deve ser rejeitado."""
        with self.assertRaises((UserError, ValidationError)):
            self._make("123.456.789")

    # ── Unicidade ─────────────────────────────────────────────────
    def test_cpf_duplicado_rejeitado(self):
        """Dois funcionários com o mesmo CPF devem ser rejeitados."""
        self._make("123.456.789-09", name="Funcionário A")
        with self.assertRaises(
            (UserError, ValidationError), msg="CPF duplicado deve lançar erro"
        ):
            self._make("123.456.789-09", name="Funcionário B")

    def test_cpf_vazio_permitido_temporariamente(self):
        """CPF vazio pode ser salvo (funcionário em cadastramento parcial)."""
        emp = self.model.create(
            {
                "name": "Sem CPF Ainda",
                "company_id": self.company.id,
            }
        )
        self.assertTrue(emp.id)


class TestPISValidacao(TransactionCase):
    """Testes de validação do PIS/PASEP."""

    def setUp(self):
        super().setUp()
        self.model = self.env["hr.employee"]
        self.company = self.env.ref("base.main_company")

    def _make(self, pis, name="Teste PIS"):
        return self.model.create(
            {
                "name": name,
                "l10n_br_cpf": "123.456.789-09",
                "l10n_br_pis": pis,
                "company_id": self.company.id,
            }
        )

    def test_pis_valido_com_formatacao(self):
        """PIS válido com pontos e traço deve ser aceito."""
        emp = self._make("123.45678.90-1")
        self.assertEqual(emp.l10n_br_pis, "123.45678.90-1")

    def test_pis_valido_apenas_numeros(self):
        """PIS só com números deve ser formatado."""
        emp = self._make("12345678901")
        self.assertEqual(emp.l10n_br_pis, "123.45678.90-1")

    def test_pis_invalido_digito_verificador(self):
        """PIS com dígito verificador errado deve ser rejeitado."""
        with self.assertRaises((UserError, ValidationError)):
            self._make("123.45678.90-0")

    def test_pis_duplicado_rejeitado(self):
        """Dois funcionários com o mesmo PIS devem ser rejeitados."""
        self._make("123.45678.90-1", name="Func A")
        # Segundo funcionário com outro CPF mas mesmo PIS
        with self.assertRaises((UserError, ValidationError)):
            self.model.create(
                {
                    "name": "Func B",
                    "l10n_br_cpf": "529.982.247-25",
                    "l10n_br_pis": "123.45678.90-1",
                    "company_id": self.company.id,
                }
            )


class TestCamposObrigatoriosBR(TransactionCase):
    """Testes de campos obrigatórios conforme tipo de contrato."""

    def setUp(self):
        super().setUp()
        self.model = self.env["hr.employee"]
        self.company = self.env.ref("base.main_company")

    def test_clt_requer_data_admissao(self):
        """Contrato CLT deve ter data de admissão."""
        emp = self.model.create(
            {
                "name": "CLT sem data",
                "l10n_br_cpf": "123.456.789-09",
                "l10n_br_tipo_contrato": "clt",
                "company_id": self.company.id,
            }
        )
        # Ao confirmar o contrato CLT deve exigir data de admissão
        with self.assertRaises((UserError, ValidationError)):
            emp._action_confirmar_admissao()

    def test_campos_ctps_obrigatorios_clt(self):
        """Funcionário CLT deve ter dados da CTPS para geração de contrato."""
        emp = self.model.create(
            {
                "name": "CLT sem CTPS",
                "l10n_br_cpf": "123.456.789-09",
                "l10n_br_tipo_contrato": "clt",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises((UserError, ValidationError)):
            emp._action_gerar_contrato_trabalho()

    def test_pcd_tipo_deficiencia_obrigatorio(self):
        """Ao marcar PCD, tipo de deficiência deve ser informado."""
        emp = self.model.create(
            {
                "name": "Funcionário PCD",
                "l10n_br_cpf": "123.456.789-09",
                "l10n_br_pcd": True,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(
            (UserError, ValidationError), msg="PCD sem tipo de deficiência deve falhar"
        ):
            emp._validate_pcd_fields()
