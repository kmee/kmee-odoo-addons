# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SstCommon


@tagged("post_install", "-at_install")
class TestSstBase(SstCommon):
    """RS-03 e RS-04: inventário de riscos, laudos e responsáveis."""

    # ── Ambiente ────────────────────────────────────────────────────────────

    def test_ambiente_info_amb(self):
        """O ambiente exporta o grupo infoAmb com a inscrição sem pontuação."""
        info = self.ambiente._to_info_amb()
        self.assertEqual(info["local_amb"], 1)
        self.assertEqual(info["dsc_setor"], "PRODUCAO")
        self.assertEqual(info["tp_insc"], 1)
        self.assertEqual(info["nr_insc"], "02546716000146")

    def test_ambiente_inscricao_invalida(self):
        """CNPJ com menos de 14 dígitos é recusado no cadastro do ambiente."""
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.ambiente"].create(
                {
                    "name": "Ambiente Inválido",
                    "dsc_setor": "TESTE",
                    "nr_insc": "12345",
                }
            )

    def test_ambiente_cno_doze_digitos(self):
        """CNO tem 12 dígitos, e não 14 como o CNPJ."""
        ambiente = self.env["l10n_br.sst.ambiente"].create(
            {
                "name": "Obra",
                "dsc_setor": "CANTEIRO",
                "tp_insc": "4",
                "nr_insc": "123456789012",
            }
        )
        self.assertEqual(ambiente._to_info_amb()["tp_insc"], 4)

    # ── Responsável ─────────────────────────────────────────────────────────

    def test_responsavel_resp_reg(self):
        """O responsável exporta o grupo respReg com CPF só de dígitos."""
        resp = self.responsavel._to_resp_reg()
        self.assertEqual(resp["cpf_resp"], "07616692941")
        self.assertEqual(resp["ide_oc"], 4)
        self.assertEqual(resp["uf_oc"], "MG")

    def test_responsavel_cpf_invalido(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.responsavel"].create(
                {"name": "Sem CPF válido", "cpf": "123"}
            )

    def test_responsavel_outros_exige_descricao(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.responsavel"].create(
                {
                    "name": "Outro Conselho",
                    "cpf": "076.166.929-41",
                    "ide_oc": "9",
                }
            )

    # ── Risco ───────────────────────────────────────────────────────────────

    def test_risco_insalubridade_exige_grau(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.risco"].create(
                {
                    "ambiente_id": self.ambiente.id,
                    "agente_nocivo_id": self.agente_ruido.id,
                    "insalubridade": True,
                    "date_from": "2026-01-01",
                }
            )

    def test_risco_nao_acumula_adicionais(self):
        """Súmula 364 do TST já no laudo, antes de chegar à folha."""
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.risco"].create(
                {
                    "ambiente_id": self.ambiente.id,
                    "agente_nocivo_id": self.agente_ruido.id,
                    "insalubridade": True,
                    "grau_insalubridade": "maximo",
                    "periculosidade": True,
                    "date_from": "2026-01-01",
                }
            )

    def test_risco_ausencia_bloqueia_epi(self):
        """Ausência de agente nocivo não convive com EPI utilizado."""
        with self.assertRaises(ValidationError):
            self.env["l10n_br.sst.risco"].create(
                {
                    "ambiente_id": self.ambiente.id,
                    "agente_nocivo_id": self.agente_ausencia.id,
                    "utiliz_epi": "2",
                    "date_from": "2026-01-01",
                }
            )

    def test_risco_ausencia_aceita_nao_se_aplica(self):
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "utiliz_epc": "0",
                "utiliz_epi": "0",
                "date_from": "2026-01-01",
            }
        )
        self.assertTrue(risco.ausencia_de_risco)

    def test_risco_vigencia_invertida(self):
        with self.assertRaises(ValidationError):
            self.risco.write({"date_to": "2025-12-31"})

    def test_risco_vigente_em(self):
        self.assertTrue(self.risco._vigente_em("2026-06-01"))
        self.assertFalse(self.risco._vigente_em("2025-06-01"))
        self.risco.date_to = "2026-03-31"
        self.assertFalse(self.risco._vigente_em("2026-06-01"))

    def test_risco_aplica_a_funcao(self):
        self.assertTrue(self.risco._aplica_a_funcao(self.job))
        self.assertFalse(self.risco._aplica_a_funcao(self.job_admin))

    def test_risco_sem_funcao_atinge_todas(self):
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ruido.id,
                "date_from": "2026-01-01",
            }
        )
        self.assertTrue(risco._aplica_a_funcao(self.job_admin))

    def test_aliquota_gilrat_maior_prevalece(self):
        """Exposto a 25 e a 15 anos, prevalece a alíquota de 12%."""
        self.assertEqual(self.risco._aliquota_gilrat_adicional(), 6.0)
        risco_15 = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ruido.id,
                "financiamento_aposent_id": self.fin_aposent_15.id,
                "date_from": "2026-01-01",
            }
        )
        self.assertEqual((self.risco | risco_15)._aliquota_gilrat_adicional(), 12.0)

    def test_aliquota_gilrat_sem_exposicao(self):
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "date_from": "2026-01-01",
            }
        )
        self.assertEqual(risco._aliquota_gilrat_adicional(), 0.0)

    # ── Laudo ───────────────────────────────────────────────────────────────

    def test_laudo_vigencia_invertida(self):
        with self.assertRaises(ValidationError):
            self.laudo.write({"date_to": "2025-01-01"})

    def test_laudo_sem_risco_nao_entra_em_vigor(self):
        laudo = self.env["l10n_br.sst.laudo"].create(
            {"name": "PGR vazio", "date_from": "2026-01-01"}
        )
        with self.assertRaises(ValidationError):
            laudo.action_vigente()

    def test_laudo_substitui_anterior(self):
        self.laudo.action_vigente()
        self.assertEqual(self.laudo.state, "vigente")
        novo = self.env["l10n_br.sst.laudo"].create(
            {
                "name": "LTCAT 2027",
                "tipo": "ltcat",
                "date_from": "2027-01-01",
                "laudo_anterior_id": self.laudo.id,
            }
        )
        self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "laudo_id": novo.id,
                "agente_nocivo_id": self.agente_ruido.id,
                "date_from": "2027-01-01",
            }
        )
        novo.action_vigente()
        self.assertEqual(self.laudo.state, "substituido")
        self.assertEqual(str(self.laudo.date_to), "2026-12-31")

    def test_laudo_agrega_ambientes(self):
        self.assertIn(self.ambiente, self.laudo.ambiente_ids)

    # ── Contrato ────────────────────────────────────────────────────────────

    def test_contrato_riscos_vigentes(self):
        riscos = self.contract._l10n_br_sst_riscos_vigentes("2026-06-01")
        self.assertIn(self.risco, riscos)

    def test_contrato_funcao_diferente_nao_pega_risco(self):
        self.contract.job_id = self.job_admin
        riscos = self.contract._l10n_br_sst_riscos_vigentes("2026-06-01")
        self.assertNotIn(self.risco, riscos)

    def test_contrato_sem_ambiente(self):
        self.contract.l10n_br_sst_ambiente_id = False
        self.assertFalse(self.contract._l10n_br_sst_riscos_vigentes("2026-06-01"))

    def test_contrato_exposicao_especial(self):
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_sst_exposicao_especial)

    def test_contrato_descricao_atividade_cai_para_ambiente(self):
        self.assertEqual(
            self.contract._l10n_br_sst_descricao_atividade(),
            "Operação de envasadora automática.",
        )
        self.contract.l10n_br_sst_descricao_atividade = "Opera a envasadora 3."
        self.assertEqual(
            self.contract._l10n_br_sst_descricao_atividade(),
            "Opera a envasadora 3.",
        )

    def test_employee_riscos_vigentes(self):
        riscos = self.employee._l10n_br_sst_riscos_vigentes("2026-06-01")
        self.assertIn(self.risco, riscos)
