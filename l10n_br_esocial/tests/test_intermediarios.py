import logging

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    import esociallib  # noqa: F401

    HAS_ESOCIALLIB = True
except ImportError:
    HAS_ESOCIALLIB = False


class TestESocialIntermediarioBase(TransactionCase):
    """Base class for intermediário tests with common setup."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        partner = cls.company.partner_id
        if not partner.cnpj_cpf:
            partner.write({"cnpj_cpf": "02.546.716/0001-46"})

        cls.cat_101 = cls.env.ref("l10n_br_esocial.cat_trab_101")
        cls.class_trib = cls.env.ref("l10n_br_esocial.class_trib_01")
        cls.lotacao_tipo = cls.env.ref("l10n_br_esocial.lot_trib_01")
        cls.mot_afast_01 = cls.env.ref("l10n_br_esocial.mot_afast_01")
        cls.mot_deslig_02 = cls.env.ref("l10n_br_esocial.mot_deslig_02")

        cls.company.write(
            {
                "l10n_br_esocial_class_trib_id": cls.class_trib.id,
                "l10n_br_esocial_lotacao_id": cls.lotacao_tipo.id,
                "l10n_br_esocial_cod_lotacao": "LOT001",
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Test eSocial Worker",
                "cnpj_cpf": "076.166.929-41",
                "l10n_br_esocial_matricula": "MAT001",
                "l10n_br_esocial_categoria_id": cls.cat_101.id,
                "gender": "male",
                "birthday": "1990-05-15",
            }
        )

        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato CLT Test",
                "employee_id": cls.employee.id,
                "wage": 5000.00,
                "date_start": "2024-01-02",
                "state": "open",
            }
        )


class TestS1000(TestESocialIntermediarioBase):
    """Testes do intermediário S-1000 (Informações do Empregador)."""

    def test_s1000_dict_structure(self):
        """Dict do S-1000 deve conter campos obrigatórios."""
        s1000 = self.env["l10n_br.esocial.s1000"].create(
            {
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        data = s1000._to_esociallib_dict()
        self.assertEqual(data["operacao"], "inclusao")
        self.assertEqual(data["ini_valid"], "2024-01")
        self.assertIn("tp_insc", data)
        self.assertIn("nr_insc", data)
        self.assertIn("class_trib", data)

    def test_s1000_requires_class_trib(self):
        """Deve dar erro se empresa não tem classificação tributária."""
        self.company.l10n_br_esocial_class_trib_id = False
        s1000 = self.env["l10n_br.esocial.s1000"].create(
            {
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1000._to_esociallib_dict()

    def test_s1000_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s1000 = self.env["l10n_br.esocial.s1000"].create(
            {
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        xml = s1000._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtInfoEmpregador", xml)


class TestS1020(TestESocialIntermediarioBase):
    """Testes do intermediário S-1020 (Tabela de Lotações)."""

    def test_s1020_dict_structure(self):
        """Dict do S-1020 deve conter campos obrigatórios."""
        s1020 = self.env["l10n_br.esocial.s1020"].create(
            {
                "operacao": "inclusao",
                "cod_lotacao": "LOT001",
                "ini_valid": "2024-01",
                "fpas": "515",
                "cod_tercs": "0115",
                "company_id": self.company.id,
            }
        )
        data = s1020._to_esociallib_dict()
        self.assertEqual(data["cod_lotacao"], "LOT001")
        self.assertEqual(data["fpas"], "515")
        self.assertEqual(data["cod_tercs"], "0115")
        self.assertIn("tp_lotacao", data)

    def test_s1020_requires_lotacao_tipo(self):
        """Deve dar erro se empresa não tem tipo lotação."""
        self.company.l10n_br_esocial_lotacao_id = False
        s1020 = self.env["l10n_br.esocial.s1020"].create(
            {
                "operacao": "inclusao",
                "cod_lotacao": "LOT001",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1020._to_esociallib_dict()

    def test_s1020_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s1020 = self.env["l10n_br.esocial.s1020"].create(
            {
                "operacao": "inclusao",
                "cod_lotacao": "LOT001",
                "ini_valid": "2024-01",
                "fpas": "515",
                "cod_tercs": "0115",
                "company_id": self.company.id,
            }
        )
        xml = s1020._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtTabLotacao", xml)


class TestS2200(TestESocialIntermediarioBase):
    """Testes do intermediário S-2200 (Admissão)."""

    def test_s2200_dict_structure(self):
        """Dict do S-2200 deve conter dados do empregado."""
        s2200 = self.env["l10n_br.esocial.s2200"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "company_id": self.company.id,
            }
        )
        data = s2200._to_esociallib_dict()
        self.assertEqual(data["cpf_trab"], "07616692941")
        self.assertEqual(data["nm_trab"], "Test eSocial Worker")
        self.assertEqual(data["sexo"], "M")
        self.assertEqual(data["matricula"], "MAT001")
        self.assertEqual(data["tp_reg_trab"], 1)
        self.assertEqual(data["vr_sal_fx"], "5000.0")
        self.assertEqual(data["dt_adm"], "2024-01-02")

    def test_s2200_requires_cpf(self):
        """Deve dar erro se empregado não tem CPF."""
        emp = self.env["hr.employee"].create(
            {
                "name": "No CPF",
                "l10n_br_esocial_matricula": "MAT099",
                "l10n_br_esocial_categoria_id": self.cat_101.id,
            }
        )
        s2200 = self.env["l10n_br.esocial.s2200"].create(
            {
                "employee_id": emp.id,
                "contract_id": self.contract.id,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s2200._to_esociallib_dict()

    def test_s2200_requires_matricula(self):
        """Deve dar erro se empregado não tem matrícula."""
        emp = self.env["hr.employee"].create(
            {
                "name": "No Matricula",
                "cnpj_cpf": "857.642.960-52",
                "l10n_br_esocial_categoria_id": self.cat_101.id,
            }
        )
        s2200 = self.env["l10n_br.esocial.s2200"].create(
            {
                "employee_id": emp.id,
                "contract_id": self.contract.id,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s2200._to_esociallib_dict()

    def test_s2200_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s2200 = self.env["l10n_br.esocial.s2200"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "company_id": self.company.id,
            }
        )
        xml = s2200._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtAdmissao", xml)
        self.assertIn("07616692941", xml)


class TestS2206(TestESocialIntermediarioBase):
    """Testes do intermediário S-2206 (Alteração Contratual)."""

    def test_s2206_dict_structure(self):
        """Dict do S-2206 deve conter dados da alteração."""
        s2206 = self.env["l10n_br.esocial.s2206"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "dt_alteracao": "2024-06-01",
                "dsc_alt": "Aumento salarial",
                "company_id": self.company.id,
            }
        )
        data = s2206._to_esociallib_dict()
        self.assertEqual(data["cpf_trab"], "07616692941")
        self.assertEqual(data["matricula"], "MAT001")
        self.assertEqual(data["dt_alteracao"], "2024-06-01")
        self.assertEqual(data["dsc_alt"], "Aumento salarial")
        self.assertEqual(data["vr_sal_fx"], "5000.0")

    def test_s2206_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s2206 = self.env["l10n_br.esocial.s2206"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "dt_alteracao": "2024-06-01",
                "company_id": self.company.id,
            }
        )
        xml = s2206._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtAltContratual", xml)


class TestS2230(TestESocialIntermediarioBase):
    """Testes do intermediário S-2230 (Afastamento)."""

    def test_s2230_dict_inicio(self):
        """Dict do S-2230 com início de afastamento."""
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "dt_ini_afast": "2024-03-01",
                "cod_mot_afast": "01",
                "company_id": self.company.id,
            }
        )
        data = s2230._to_esociallib_dict()
        self.assertEqual(data["cpf_trab"], "07616692941")
        self.assertEqual(data["dt_ini_afast"], "2024-03-01")
        self.assertEqual(data["cod_mot_afast"], "01")

    def test_s2230_dict_termino(self):
        """Dict do S-2230 com término de afastamento."""
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "dt_term_afast": "2024-03-15",
                "company_id": self.company.id,
            }
        )
        data = s2230._to_esociallib_dict()
        self.assertEqual(data["dt_term_afast"], "2024-03-15")
        self.assertNotIn("dt_ini_afast", data)

    def test_s2230_requires_dates(self):
        """Deve dar erro se não tem data de início nem término."""
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s2230._to_esociallib_dict()

    def test_s2230_requires_motivo_for_inicio(self):
        """Deve dar erro se início sem motivo."""
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "dt_ini_afast": "2024-03-01",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s2230._to_esociallib_dict()

    def test_s2230_motivo_from_m2o(self):
        """Deve usar código do M2O motivo se cod_mot_afast vazio."""
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "dt_ini_afast": "2024-03-01",
                "motivo_afastamento_id": self.mot_afast_01.id,
                "company_id": self.company.id,
            }
        )
        data = s2230._to_esociallib_dict()
        self.assertEqual(data["cod_mot_afast"], "01")

    def test_s2230_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s2230 = self.env["l10n_br.esocial.s2230"].create(
            {
                "employee_id": self.employee.id,
                "dt_ini_afast": "2024-03-01",
                "cod_mot_afast": "01",
                "company_id": self.company.id,
            }
        )
        xml = s2230._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtAfastTemp", xml)


class TestS2299(TestESocialIntermediarioBase):
    """Testes do intermediário S-2299 (Desligamento)."""

    def test_s2299_dict_structure(self):
        """Dict do S-2299 deve conter dados do desligamento."""
        s2299 = self.env["l10n_br.esocial.s2299"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "dt_deslig": "2024-12-31",
                "motivo_desligamento_id": self.mot_deslig_02.id,
                "company_id": self.company.id,
            }
        )
        data = s2299._to_esociallib_dict()
        self.assertEqual(data["cpf_trab"], "07616692941")
        self.assertEqual(data["matricula"], "MAT001")
        self.assertEqual(data["dt_deslig"], "2024-12-31")
        self.assertEqual(data["mtv_deslig"], "02")
        self.assertEqual(data["ind_pagto_api"], "N")

    def test_s2299_with_aviso_previo(self):
        """Dict do S-2299 com aviso prévio indenizado."""
        s2299 = self.env["l10n_br.esocial.s2299"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "dt_deslig": "2024-12-31",
                "motivo_desligamento_id": self.mot_deslig_02.id,
                "ind_pagto_api": "S",
                "dt_proj_fim_api": "2025-01-30",
                "company_id": self.company.id,
            }
        )
        data = s2299._to_esociallib_dict()
        self.assertEqual(data["ind_pagto_api"], "S")
        self.assertEqual(data["dt_proj_fim_api"], "2025-01-30")

    def test_s2299_gerar_xml(self):
        """Deve gerar XML via esociallib."""
        if not HAS_ESOCIALLIB:
            return
        s2299 = self.env["l10n_br.esocial.s2299"].create(
            {
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "dt_deslig": "2024-12-31",
                "motivo_desligamento_id": self.mot_deslig_02.id,
                "company_id": self.company.id,
            }
        )
        xml = s2299._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("evtDeslig", xml)
