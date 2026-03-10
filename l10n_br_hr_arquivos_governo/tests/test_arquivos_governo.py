from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestDirf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.employee = cls.env.ref("l10n_br_hr.demo_employee_joao")
        cls.contract = cls.env.ref("l10n_br_hr_contract.demo_contract_joao")

    def _create_dirf(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "ano_referencia": 2025,
            "ano_calendario": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.dirf"].create(vals)

    def test_dirf_create(self):
        """Cria registro DIRF."""
        dirf = self._create_dirf()
        self.assertEqual(dirf.state, "draft")
        self.assertIn("DIRF", dirf.name)

    def test_dirf_workflow(self):
        """Testa transições de estado."""
        dirf = self._create_dirf()
        dirf.action_open()
        self.assertEqual(dirf.state, "open")
        dirf.action_sent()
        self.assertEqual(dirf.state, "sent")
        dirf.action_draft()
        self.assertEqual(dirf.state, "draft")

    def test_dirf_gerar_sem_funcionarios_falha(self):
        """Gerar DIRF sem funcionários deve falhar."""
        dirf = self._create_dirf()
        with self.assertRaises(UserError):
            dirf.action_gerar_dirf()

    def test_dirf_buscar_e_gerar(self):
        """Busca funcionários e gera DIRF com holerite existente."""
        payslip = self.env["hr.payslip"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "struct_id": self.contract.struct_id.id,
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "name": "Holerite DIRF Test",
            }
        )
        payslip.compute_sheet()
        payslip.action_payslip_done()

        dirf = self._create_dirf()
        dirf.action_buscar_funcionarios()
        self.assertIn(self.employee, dirf.employee_ids)

        dirf.action_gerar_dirf()
        self.assertEqual(dirf.state, "open")
        self.assertTrue(dirf.file_content)
        self.assertIn("DIRF|", dirf.file_content)
        self.assertIn("BPFDEC|", dirf.file_content)
        self.assertIn("FIMDirf|", dirf.file_content)

    def test_dirf_retificadora(self):
        """DIRF retificadora tem campo de recibo."""
        dirf = self._create_dirf(retificadora=True, numero_recibo="12345")
        self.assertTrue(dirf.retificadora)
        self.assertEqual(dirf.numero_recibo, "12345")


class TestSefip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.employee = cls.env.ref("l10n_br_hr.demo_employee_joao")
        cls.contract = cls.env.ref("l10n_br_hr_contract.demo_contract_joao")

    def _create_sefip(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "mes": "1",
            "ano": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.sefip"].create(vals)

    def test_sefip_create(self):
        """Cria registro SEFIP."""
        sefip = self._create_sefip()
        self.assertEqual(sefip.state, "draft")
        self.assertIn("SEFIP", sefip.name)

    def test_sefip_sem_holerites_falha(self):
        """Gerar SEFIP sem holerites deve falhar."""
        sefip = self._create_sefip(mes="6", ano=2099)
        with self.assertRaises(UserError):
            sefip.action_gerar_sefip()

    def test_sefip_gerar_com_holerite(self):
        """Gera SEFIP com holerite existente."""
        payslip = self.env["hr.payslip"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "struct_id": self.contract.struct_id.id,
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "name": "Holerite SEFIP Test",
            }
        )
        payslip.compute_sheet()
        payslip.action_payslip_done()

        sefip = self._create_sefip()
        sefip.action_gerar_sefip()
        self.assertEqual(sefip.state, "open")
        self.assertTrue(sefip.file_content)
        # Nome é normalizado (sem acentos) no arquivo SEFIP
        self.assertIn("JOAO", sefip.file_content.upper()[:500])

    def test_sefip_workflow(self):
        """Testa transições de estado SEFIP."""
        sefip = self._create_sefip()
        sefip.action_open()
        self.assertEqual(sefip.state, "open")
        sefip.action_sent()
        self.assertEqual(sefip.state, "sent")


class TestCaged(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.employee = cls.env.ref("l10n_br_hr.demo_employee_joao")
        cls.contract = cls.env.ref("l10n_br_hr_contract.demo_contract_joao")

    def _create_caged(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "mes": "1",
            "ano": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.caged"].create(vals)

    def test_caged_create(self):
        """Cria registro CAGED."""
        caged = self._create_caged()
        self.assertEqual(caged.state, "draft")
        self.assertIn("CAGED", caged.name)

    def test_caged_sem_movimentacoes_falha(self):
        """Gerar CAGED sem movimentações deve falhar."""
        caged = self._create_caged(mes="6", ano=2099)
        with self.assertRaises(UserError):
            caged.action_gerar_caged()

    def test_caged_gerar_admissao(self):
        """Gera CAGED com admissão no período."""
        caged = self._create_caged()
        caged.action_gerar_caged()
        self.assertEqual(caged.state, "open")
        self.assertTrue(caged.file_content)
        # Registro A deve estar presente
        self.assertTrue(caged.file_content.startswith("A"))

    def test_caged_workflow(self):
        """Testa transições de estado CAGED."""
        caged = self._create_caged()
        caged.action_open()
        self.assertEqual(caged.state, "open")
        caged.action_sent()
        self.assertEqual(caged.state, "sent")

    def test_constantes_categorias(self):
        """Verifica que constantes de categoria estão carregadas."""
        from ..models.constantes_rh import (
            CATEGORIA_TRABALHADOR,
            SEFIP_CATEGORIA_TRABALHADOR,
        )

        self.assertTrue(len(CATEGORIA_TRABALHADOR) > 20)
        self.assertEqual(SEFIP_CATEGORIA_TRABALHADOR["103"], "07")  # aprendiz
        self.assertEqual(SEFIP_CATEGORIA_TRABALHADOR["721"], "11")  # diretor s/ FGTS
