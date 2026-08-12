# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestS1020Lotacao(ESocialCicloCommon):
    """S-1020: FPAS e terceiros são da lotação tributária, não do estabelecimento."""

    def setUp(self):
        super().setUp()
        # O cenário comum usa classificação 01 (Simples). Os testes de FPAS com
        # terceiros devidos precisam de empresa fora do Simples.
        self.class_trib_agro = self.env.ref("l10n_br_esocial.class_trib_06")
        self.class_trib_simples = self.env.ref("l10n_br_esocial.class_trib_01")

    def _criar_s1020(self, **kwargs):
        vals = {
            "cod_lotacao": "LOT001",
            "ini_valid": "2024-01",
            "fpas": "515",
            "cod_tercs": "0079",
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s1020"].create(vals)

    # ── Contrato de encargos (RF-31) ───────────────────────────────────────

    def test_parametros_encargos_traz_fpas_e_terceiros(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_agro
        s1020 = self._criar_s1020()
        params = s1020.get_parametros_encargos()
        self.assertEqual(params["fpas"], "515")
        self.assertEqual(params["cod_tercs"], "0079")
        self.assertEqual(params["cod_lotacao"], "LOT001")
        self.assertFalse(params["terceiros_dispensados"])
        # GILRAT não é da lotação: ele vem do estabelecimento (S-1005).
        self.assertNotIn("aliq_rat", params)
        self.assertNotIn("fap", params)

    def test_simples_marca_terceiros_dispensados(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_simples
        s1020 = self._criar_s1020(cod_tercs="0000")
        self.assertTrue(s1020.get_parametros_encargos()["terceiros_dispensados"])

    # ── Validações ─────────────────────────────────────────────────────────

    def test_fpas_ausente_nao_cai_em_padrao(self):
        """FPAS define a contribuição devida: não pode ter default silencioso."""
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_agro
        s1020 = self._criar_s1020(fpas=False)
        with self.assertRaises(UserError) as erro:
            s1020._to_esociallib_dict()
        self.assertIn("FPAS", str(erro.exception))

    def test_terceiros_ausente_fora_do_simples(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_agro
        s1020 = self._criar_s1020(cod_tercs=False)
        with self.assertRaises(UserError):
            s1020._to_esociallib_dict()

    def test_simples_com_terceiros_e_recusado(self):
        """Simples não recolhe terceiros (LC 123 art. 13, § 3º): codTercs 0000."""
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_simples
        s1020 = self._criar_s1020(cod_tercs="0079")
        with self.assertRaises(UserError) as erro:
            s1020._to_esociallib_dict()
        self.assertIn("0000", str(erro.exception))

    def test_simples_sem_terceiros_assume_zero(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_simples
        s1020 = self._criar_s1020(cod_tercs=False)
        data = s1020._to_esociallib_dict()
        self.assertEqual(data["cod_tercs"], "0000")

    def test_terceiros_suspensos_no_dict(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_agro
        s1020 = self._criar_s1020(cod_tercs_susp="0064")
        data = s1020._to_esociallib_dict()
        self.assertEqual(data["cod_tercs_susp"], "0064")

    def test_exclusao_dispensa_fpas(self):
        s1020 = self._criar_s1020(operacao="exclusao", fpas=False, cod_tercs=False)
        data = s1020._to_esociallib_dict()
        self.assertNotIn("fpas", data)
        self.assertNotIn("cod_tercs", data)

    def test_competencia_invalida(self):
        with self.assertRaises(ValidationError):
            self._criar_s1020(ini_valid="2024-13")

    # ── Vigência ───────────────────────────────────────────────────────────

    def test_buscar_vigente(self):
        antigo = self._criar_s1020(ini_valid="2023-01", fim_valid="2023-12")
        atual = self._criar_s1020(ini_valid="2024-01")
        modelo = self.env["l10n_br.esocial.s1020"]
        self.assertEqual(
            modelo.buscar_vigente(self.company, "LOT001", "2023-06"), antigo
        )
        self.assertEqual(
            modelo.buscar_vigente(self.company, "LOT001", "2024-03"), atual
        )
        self.assertFalse(modelo.buscar_vigente(self.company, "LOT001", "2022-12"))

    def test_xml_leva_fpas_na_lotacao(self):
        self.company.l10n_br_esocial_class_trib_id = self.class_trib_agro
        s1020 = self._criar_s1020()
        data = s1020._to_esociallib_dict()
        self.assertEqual(data["fpas"], "515")
        self.assertEqual(data["cod_tercs"], "0079")
        self.assertIn("tp_lotacao", data)
