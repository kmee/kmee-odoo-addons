from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.constantes_rh import (
    CODIGOS_FGTS,
    CODIGOS_INSS,
    CODIGOS_IRRF,
    CODIGOS_REMUNERACAO_BRUTA,
)

#: Salário do contrato de teste: sem adicionais nem salário-família,
#: a remuneração bruta (GROSS) é exatamente este valor.
SALARIO_TESTE = 5000.00

#: Logger onde os avisos de rubrica ausente são registrados.
LOGGER_RUBRICAS = "odoo.addons.l10n_br_hr_arquivos_governo.models.rubricas"


class ArquivosGovernoCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
            )
        )
        cls.company = cls.env.ref("base.main_company")
        cls.employee = cls.env.ref("l10n_br_hr.demo_employee_joao")
        cls.contract = cls.env.ref("l10n_br_hr_contract.demo_contract_joao")
        cls.struct_clt = cls.env.ref("l10n_br_hr_payroll.structure_clt")
        cls.cat_gross = cls.env.ref("l10n_br_hr_payroll.hr_salary_rule_category_gross")
        cls.cat_ded = cls.env.ref("l10n_br_hr_payroll.hr_salary_rule_category_ded")
        cls.cat_comp = cls.env.ref("l10n_br_hr_payroll.hr_salary_rule_category_comp")

        # Empregado/contrato determinístico: nenhum adicional, nenhum
        # dependente e nenhum filho para salário-família, de modo que
        # GROSS == SALARIO_TESTE.
        cls.employee_valor = cls.env["hr.employee"].create(
            {
                "name": "Funcionario Valor Conhecido",
                "company_id": cls.company.id,
                "country_id": cls.env.ref("base.br").id,
                "l10n_br_tipo_contrato": "clt",
                "l10n_br_irrf_dependentes": 0,
                "l10n_br_num_filhos_sf": 0,
            }
        )
        cls.contract_valor = cls.env["hr.contract"].create(
            {
                "name": "Contrato Valor Conhecido",
                "employee_id": cls.employee_valor.id,
                "company_id": cls.company.id,
                "wage": SALARIO_TESTE,
                "date_start": "2024-01-02",
                "state": "open",
                "struct_id": cls.struct_clt.id,
            }
        )

    @classmethod
    def _criar_holerite(
        cls,
        contract,
        date_from,
        date_to,
        struct=None,
        name="Holerite Teste",
    ):
        """Cria, calcula e fecha um holerite."""
        payslip = cls.env["hr.payslip"].create(
            {
                "name": name,
                "employee_id": contract.employee_id.id,
                "contract_id": contract.id,
                "struct_id": (struct or contract.struct_id).id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        payslip.compute_sheet()
        payslip.action_payslip_done()
        return payslip

    @classmethod
    def _criar_estrutura_13(cls):
        """Estrutura de 13º salário com valores fixos e códigos do 13º.

        Reproduz os códigos usados em ``l10n_br_hr_vacation``
        (GROSS / INSS_13 / IRRF_13 / FGTS) sem depender daquele módulo.
        """

        def _regra(name, code, category, valor, sequence):
            return cls.env["hr.salary.rule"].create(
                {
                    "name": name,
                    "code": code,
                    "sequence": sequence,
                    "category_id": category.id,
                    "condition_select": "none",
                    "amount_select": "fix",
                    "amount_fix": valor,
                }
            )

        regras = (
            _regra("13 Bruto", "GROSS", cls.cat_gross, SALARIO_TESTE, 99)
            | _regra("13 INSS", "INSS_13", cls.cat_ded, 400.0, 100)
            | _regra("13 IRRF", "IRRF_13", cls.cat_ded, 100.0, 120)
            | _regra("13 FGTS", "FGTS", cls.cat_comp, 400.0, 150)
        )
        return cls.env["hr.payroll.structure"].create(
            {
                "name": "13o Salario (Teste)",
                "code": "TESTE_13",
                "company_id": cls.company.id,
                "rule_ids": [(6, 0, regras.ids)],
            }
        )

    @classmethod
    def _criar_estrutura_sem_bruto(cls):
        """Estrutura sem nenhuma rubrica de remuneração bruta."""
        regra = cls.env["hr.salary.rule"].create(
            {
                "name": "Verba Desconhecida",
                "code": "VERBA_INEXISTENTE",
                "sequence": 10,
                "category_id": cls.cat_ded.id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": 100.0,
            }
        )
        return cls.env["hr.payroll.structure"].create(
            {
                "name": "Estrutura sem bruto (Teste)",
                "code": "TESTE_SEM_BRUTO",
                "company_id": cls.company.id,
                "rule_ids": [(6, 0, regra.ids)],
            }
        )

    @staticmethod
    def _centavos(valor, size=15):
        """Mesma formatação usada nos arquivos: centavos com zeros à esquerda."""
        return str(int(round(abs(valor) * 100, 0))).zfill(size)

    @staticmethod
    def _valor_rubrica(payslip, codigos):
        """Total das linhas do holerite com os códigos informados."""
        linhas = payslip.line_ids.filtered(lambda line: line.code in codigos)
        return sum(linhas.mapped("total"))


@tagged("post_install", "-at_install")
class TestDirf(ArquivosGovernoCommon):
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
        self._criar_holerite(
            self.contract, "2024-01-01", "2024-01-31", name="Holerite DIRF Test"
        )

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

    def test_dirf_valores_mensais(self):
        """RTRT/RTPO/RTDP devem trazer os VALORES do holerite, não zeros."""
        payslip = self._criar_holerite(
            self.contract_valor, "2024-03-01", "2024-03-31", name="Holerite 03/2024"
        )
        bruto = self._valor_rubrica(payslip, CODIGOS_REMUNERACAO_BRUTA)
        inss = self._valor_rubrica(payslip, CODIGOS_INSS)
        irrf = self._valor_rubrica(payslip, CODIGOS_IRRF)
        # Pré-condições: as rubricas existem e têm valor.
        self.assertEqual(bruto, SALARIO_TESTE)
        self.assertGreater(inss, 0.0)
        self.assertGreater(irrf, 0.0)

        dirf = self._create_dirf()
        dirf.employee_ids = self.employee_valor
        dirf.action_gerar_dirf()

        linhas = dirf.file_content.split("\r\n")
        rtrt = [line for line in linhas if line.startswith("RTRT|")]
        rtpo = [line for line in linhas if line.startswith("RTPO|")]
        rtdp = [line for line in linhas if line.startswith("RTDP|")]
        self.assertEqual(len(rtrt), 12)
        self.assertEqual(len(rtpo), 12)
        self.assertEqual(len(rtdp), 12)

        # Março (índice 2) traz os valores; os demais meses ficam zerados.
        self.assertEqual(rtrt[2], "RTRT|000000000500000|")
        self.assertEqual(rtrt[2], "RTRT|%s|" % self._centavos(bruto))
        self.assertEqual(rtpo[2], "RTPO|%s|" % self._centavos(inss))
        self.assertEqual(rtdp[2], "RTDP|%s|" % self._centavos(irrf))
        self.assertEqual(rtrt[0], "RTRT|%s|" % ("0" * 15))
        # Regressão do bug de rubrica inexistente ("BRUTO"): o mês com
        # holerite não pode sair zerado.
        self.assertNotEqual(rtrt[2], "RTRT|%s|" % ("0" * 15))

    def test_dirf_valores_13_salario(self):
        """13º salário: INSS_13/IRRF_13 devem ser somados nos registros."""
        struct_13 = self._criar_estrutura_13()
        payslip = self._criar_holerite(
            self.contract_valor,
            "2024-12-01",
            "2024-12-31",
            struct=struct_13,
            name="13o Salario 2024",
        )
        self.assertEqual(self._valor_rubrica(payslip, CODIGOS_INSS), 400.0)
        self.assertEqual(self._valor_rubrica(payslip, CODIGOS_IRRF), 100.0)

        dirf = self._create_dirf()
        dirf.employee_ids = self.employee_valor
        dirf.action_gerar_dirf()

        linhas = dirf.file_content.split("\r\n")
        rtrt = [line for line in linhas if line.startswith("RTRT|")]
        rtpo = [line for line in linhas if line.startswith("RTPO|")]
        rtdp = [line for line in linhas if line.startswith("RTDP|")]
        # Dezembro = índice 11
        self.assertEqual(rtrt[11], "RTRT|000000000500000|")
        self.assertEqual(rtpo[11], "RTPO|%s|" % self._centavos(400.0))
        self.assertEqual(rtdp[11], "RTDP|%s|" % self._centavos(100.0))

    def test_dirf_rubrica_bruta_ausente_falha_alto(self):
        """Sem rubrica de remuneração bruta: aviso no log e UserError."""
        struct = self._criar_estrutura_sem_bruto()
        self._criar_holerite(
            self.contract_valor,
            "2024-04-01",
            "2024-04-30",
            struct=struct,
            name="Holerite sem bruto",
        )
        dirf = self._create_dirf()
        dirf.employee_ids = self.employee_valor
        with self.assertLogs(LOGGER_RUBRICAS, level="WARNING") as log:
            with self.assertRaises(UserError):
                dirf.action_gerar_dirf()
        self.assertTrue(
            any("GROSS" in mensagem for mensagem in log.output),
            "O aviso de rubrica ausente deve citar o código GROSS.",
        )


@tagged("post_install", "-at_install")
class TestSefip(ArquivosGovernoCommon):
    def _create_sefip(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "mes": "1",
            "ano": 2024,
        }
        vals.update(kwargs)
        return self.env["l10n_br.hr.sefip"].create(vals)

    @staticmethod
    def _registros_30(sefip):
        return [
            line for line in sefip.file_content.split("\r\n") if line.startswith("30")
        ]

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
        self._criar_holerite(
            self.contract, "2024-01-01", "2024-01-31", name="Holerite SEFIP Test"
        )

        sefip = self._create_sefip()
        sefip.action_gerar_sefip()
        self.assertEqual(sefip.state, "open")
        self.assertTrue(sefip.file_content)
        # Nome é normalizado (sem acentos) no arquivo SEFIP
        self.assertIn("JOAO", sefip.file_content.upper())

    def test_sefip_workflow(self):
        """Testa transições de estado SEFIP."""
        sefip = self._create_sefip()
        sefip.action_open()
        self.assertEqual(sefip.state, "open")
        sefip.action_sent()
        self.assertEqual(sefip.state, "sent")

    def test_sefip_valores_registro_30(self):
        """Registro 30 deve conter remuneração, INSS e FGTS do holerite."""
        payslip = self._criar_holerite(
            self.contract_valor, "2024-02-01", "2024-02-29", name="Holerite 02/2024"
        )
        bruto = self._valor_rubrica(payslip, CODIGOS_REMUNERACAO_BRUTA)
        inss = self._valor_rubrica(payslip, CODIGOS_INSS)
        fgts = self._valor_rubrica(payslip, CODIGOS_FGTS)
        self.assertEqual(bruto, SALARIO_TESTE)
        self.assertGreater(inss, 0.0)
        self.assertEqual(fgts, SALARIO_TESTE * 0.08)

        sefip = self._create_sefip(mes="2")
        sefip.action_gerar_sefip()

        registros = self._registros_30(sefip)
        self.assertEqual(len(registros), 1)
        registro = registros[0]
        # Posições do registro 30: "30" + PIS(11) + nome(70) + 3 valores(15)
        remuneracao_arquivo = registro[83:98]
        inss_arquivo = registro[98:113]
        fgts_arquivo = registro[113:128]
        self.assertEqual(remuneracao_arquivo, "000000000500000")
        self.assertEqual(remuneracao_arquivo, self._centavos(bruto))
        self.assertEqual(inss_arquivo, self._centavos(inss))
        self.assertEqual(fgts_arquivo, self._centavos(fgts))
        self.assertEqual(fgts_arquivo, "000000000040000")
        # Regressão do bug de rubrica inexistente ("BRUTO").
        self.assertNotEqual(remuneracao_arquivo, "0" * 15)

    def test_sefip_valores_13_salario(self):
        """13º salário: remuneração e INSS_13 entram no registro 30."""
        struct_13 = self._criar_estrutura_13()
        self._criar_holerite(
            self.contract_valor,
            "2024-12-01",
            "2024-12-31",
            struct=struct_13,
            name="13o Salario 2024",
        )

        sefip = self._create_sefip(mes="12")
        sefip.action_gerar_sefip()

        registros = self._registros_30(sefip)
        self.assertEqual(len(registros), 1)
        registro = registros[0]
        self.assertEqual(registro[83:98], self._centavos(SALARIO_TESTE))
        self.assertEqual(registro[98:113], self._centavos(400.0))
        self.assertEqual(registro[113:128], self._centavos(400.0))

    def test_sefip_rubrica_bruta_ausente_falha_alto(self):
        """Sem rubrica de remuneração bruta: aviso no log e UserError."""
        struct = self._criar_estrutura_sem_bruto()
        self._criar_holerite(
            self.contract_valor,
            "2024-05-01",
            "2024-05-31",
            struct=struct,
            name="Holerite sem bruto",
        )
        sefip = self._create_sefip(mes="5")
        with self.assertLogs(LOGGER_RUBRICAS, level="WARNING") as log:
            with self.assertRaises(UserError):
                sefip.action_gerar_sefip()
        self.assertTrue(
            any("GROSS" in mensagem for mensagem in log.output),
            "O aviso de rubrica ausente deve citar o código GROSS.",
        )


@tagged("post_install", "-at_install")
class TestCaged(ArquivosGovernoCommon):
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
