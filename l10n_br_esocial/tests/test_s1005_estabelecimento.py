# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import HAS_ESOCIALLIB, ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestS1005Estabelecimento(ESocialCicloCommon):
    """S-1005: tabela de estabelecimentos e parâmetros de encargos."""

    def _criar_s1005(self, **kwargs):
        vals = {
            "nr_insc_estab": "02546716000146",
            "ini_valid": "2024-01",
            "cnae_prep": "4751201",
            "aliq_rat": "2",
            "fap": 1.5,
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s1005"].create(vals)

    # ── Encargos patronais (contrato do RF-31) ─────────────────────────────

    def test_rat_ajustado(self):
        """RAT ajustado é RAT x FAP — é a alíquota efetiva do GILRAT."""
        s1005 = self._criar_s1005()
        self.assertAlmostEqual(s1005.aliq_rat_ajust, 3.0, places=4)

    def test_rat_ajustado_sem_fap_usa_fator_neutro(self):
        """FAP vazio não pode zerar o GILRAT: equivale a 1,0000."""
        s1005 = self._criar_s1005(fap=0.0)
        self.assertAlmostEqual(s1005.aliq_rat_ajust, 2.0, places=4)

    def test_rat_ajustado_sem_rat(self):
        s1005 = self._criar_s1005(aliq_rat=False, fap=1.5)
        self.assertEqual(s1005.aliq_rat_ajust, 0.0)

    def test_parametros_encargos(self):
        """get_parametros_encargos é o contrato lido pelos encargos (RF-31)."""
        s1005 = self._criar_s1005()
        params = s1005.get_parametros_encargos()
        self.assertEqual(params["aliq_rat"], 2.0)
        self.assertAlmostEqual(params["fap"], 1.5, places=4)
        self.assertAlmostEqual(params["aliq_rat_ajust"], 3.0, places=4)
        self.assertEqual(params["nr_insc_estab"], "02546716000146")

    def test_estabelecimento_nao_carrega_fpas_nem_terceiros(self):
        """FPAS e terceiros são da lotação (S-1020), não do estabelecimento.

        O S-1005 leva apenas o grupo aliqGilrat; modelar FPAS aqui levaria a
        transmitir contribuição de terceiros no evento errado.
        """
        campos = self.env["l10n_br.esocial.s1005"]._fields
        for campo in ("fpas", "cod_tercs", "cod_tercs_susp"):
            self.assertNotIn(campo, campos)
        params = self._criar_s1005().get_parametros_encargos()
        self.assertNotIn("fpas", params)
        self.assertNotIn("cod_tercs", params)

    def test_fap_fora_da_faixa(self):
        """FAP legal vai de 0,5 a 2,0 — fora disso é erro de cadastro."""
        with self.assertRaises(ValidationError):
            self._criar_s1005(fap=2.5)
        with self.assertRaises(ValidationError):
            self._criar_s1005(fap=0.4)

    def test_competencia_invalida(self):
        with self.assertRaises(ValidationError):
            self._criar_s1005(ini_valid="2024-13")
        with self.assertRaises(ValidationError):
            self._criar_s1005(ini_valid="03/2024")

    # ── Vigência ───────────────────────────────────────────────────────────

    def test_buscar_vigente_respeita_periodo(self):
        antigo = self._criar_s1005(ini_valid="2023-01", fim_valid="2023-12")
        atual = self._criar_s1005(ini_valid="2024-01")
        modelo = self.env["l10n_br.esocial.s1005"]
        self.assertEqual(
            modelo.buscar_vigente(self.company, "02546716000146", "2023-06"),
            antigo,
        )
        self.assertEqual(
            modelo.buscar_vigente(self.company, "02546716000146", "2024-03"),
            atual,
        )
        self.assertFalse(
            modelo.buscar_vigente(self.company, "02546716000146", "2022-01")
        )

    def test_buscar_vigente_ignora_exclusao(self):
        self._criar_s1005(ini_valid="2024-01", operacao="exclusao")
        self.assertFalse(
            self.env["l10n_br.esocial.s1005"].buscar_vigente(
                self.company, "02546716000146", "2024-03"
            )
        )

    # ── Dicionário e XML ───────────────────────────────────────────────────

    def test_dict_inclusao(self):
        s1005 = self._criar_s1005()
        data = s1005._to_esociallib_dict()
        self.assertEqual(data["operacao"], "inclusao")
        self.assertEqual(data["tp_insc_estab"], 1)
        self.assertEqual(data["nr_insc_estab"], "02546716000146")
        self.assertEqual(data["cnae_prep"], "4751201")
        self.assertEqual(data["aliq_rat"], 2)
        self.assertEqual(data["fap"], "1.5000")

    def test_dict_exclusao_dispensa_cnae(self):
        """Exclusão só identifica o estabelecimento, sem dadosEstab."""
        s1005 = self._criar_s1005(operacao="exclusao", cnae_prep=False)
        data = s1005._to_esociallib_dict()
        self.assertNotIn("cnae_prep", data)
        self.assertNotIn("aliq_rat", data)

    def test_inclusao_exige_cnae(self):
        s1005 = self._criar_s1005(cnae_prep=False)
        with self.assertRaises(UserError):
            s1005._to_esociallib_dict()

    def test_caepf_exige_tipo(self):
        s1005 = self._criar_s1005(tp_insc_estab="3")
        with self.assertRaises(UserError):
            s1005._to_esociallib_dict()

    def test_dict_alteracao_com_nova_validade(self):
        s1005 = self._criar_s1005(
            operacao="alteracao", nova_ini_valid="2024-04", nova_fim_valid="2024-12"
        )
        data = s1005._to_esociallib_dict()
        self.assertEqual(data["nova_ini_valid"], "2024-04")
        self.assertEqual(data["nova_fim_valid"], "2024-12")

    def test_gerar_evento_produz_xml_com_rat(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        s1005 = self._criar_s1005()
        evento = s1005.action_gerar_evento()
        self.assertEqual(evento.tipo, "S-1005")
        self.assertTrue(evento.id_evento)
        raiz = etree.fromstring(evento.xml_envio.encode("utf-8"))
        valores = {}
        for elemento in raiz.iter():
            tag = elemento.tag.rsplit("}", 1)[-1]
            valores.setdefault(tag, []).append((elemento.text or "").strip())
        self.assertEqual(valores["cnaePrep"], ["4751201"])
        self.assertEqual(valores["aliqRat"], ["2"])
        self.assertEqual(valores["fap"], ["1.5000"])
        # CNPJ raiz do empregador e inscrição completa do estabelecimento.
        raiz_empregador = "".join(
            c for c in self.company.partner_id.cnpj_cpf if c.isdigit()
        )[:8]
        self.assertEqual(valores["nrInsc"], [raiz_empregador, "02546716000146"])
