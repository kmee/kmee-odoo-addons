# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import HAS_ESOCIALLIB, RECIBO_S1200, ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestS1210Pagamentos(ESocialCicloCommon):
    """S-1210: pagamentos de rendimentos do trabalho (regime de caixa)."""

    def _s1200_aceito(self, payslip):
        """Gera o S-1200 do holerite e simula o aceite pelo governo."""
        payslip.action_esocial_gerar_s1200()
        s1200 = payslip.l10n_br_esocial_s1200_id
        s1200.evento_id.write({"state": "success", "nr_recibo": RECIBO_S1200})
        return s1200

    # ── Regime de caixa ────────────────────────────────────────────────────

    def test_exige_data_de_pagamento(self):
        """Sem data de pagamento não há regime de caixa — e não há S-1210."""
        payslip = self._criar_payslip()
        self._s1200_aceito(payslip)
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1210()

    def test_competencia_vem_da_data_de_pagamento(self):
        """Folha de março paga em abril gera S-1210 na competência 2024-04."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        self._s1200_aceito(payslip)
        payslip.action_esocial_gerar_s1210()
        s1210 = payslip.l10n_br_esocial_s1210_id
        self.assertEqual(s1210.per_apur, "2024-04")
        self.assertEqual(len(s1210.pagamento_ids), 1)
        pagamento = s1210.pagamento_ids
        self.assertEqual(pagamento.per_ref, "2024-03")
        self.assertEqual(pagamento.dt_pgto.strftime("%Y-%m-%d"), "2024-04-05")

    def test_demonstrativo_aponta_para_o_s1200(self):
        """O ideDmDev do pagamento é o mesmo informado no S-1200."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        s1200 = self._s1200_aceito(payslip)
        payslip.action_esocial_gerar_s1210()
        pagamento = payslip.l10n_br_esocial_s1210_id.pagamento_ids
        self.assertEqual(pagamento.ide_dm_dev, s1200.get_ide_dm_dev())
        self.assertEqual(pagamento.s1200_id, s1200)

    def test_valor_liquido_vem_da_rubrica_net(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        self._s1200_aceito(payslip)
        payslip.action_esocial_gerar_s1210()
        s1210 = payslip.l10n_br_esocial_s1210_id
        self.assertAlmostEqual(s1210.vr_liq_total, 2584.8, places=2)

    def test_sem_rubrica_net(self):
        payslip = self._criar_payslip(
            linhas=[("GROSS", 3000.0)], data_pagamento="2024-04-05"
        )
        self._s1200_aceito(payslip)
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1210()

    # ── Dependência do S-1200 ──────────────────────────────────────────────

    def test_exige_s1200_gerado(self):
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1210()

    def test_exige_s1200_aceito(self):
        """O governo rejeita pagamento cujo demonstrativo ele não conhece."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        payslip.action_esocial_gerar_s1200()
        self.assertEqual(payslip.l10n_br_esocial_s1200_id.evento_id.state, "draft")
        with self.assertRaises(UserError):
            payslip.action_esocial_gerar_s1210()

    # ── Validações do próprio evento ───────────────────────────────────────

    def _criar_s1210(self, **kwargs):
        vals = {
            "employee_id": self.employee.id,
            "per_apur": "2024-04",
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s1210"].create(vals)

    def test_sem_pagamento_nao_gera(self):
        s1210 = self._criar_s1210()
        with self.assertRaises(UserError):
            s1210._to_esociallib_dict()

    def test_retificacao_exige_recibo(self):
        s1210 = self._criar_s1210(
            ind_retif="2",
            pagamento_ids=[
                (
                    0,
                    0,
                    {
                        "dt_pgto": "2024-04-05",
                        "per_ref": "2024-03",
                        "ide_dm_dev": "DEM000001",
                        "vr_liq": 2584.8,
                    },
                )
            ],
        )
        with self.assertRaises(UserError):
            s1210._to_esociallib_dict()

    def test_recibo_em_formato_invalido(self):
        with self.assertRaises(ValidationError):
            self._criar_s1210(ind_retif="2", nr_recibo="1.2.202404.0001")

    def test_valor_liquido_precisa_ser_positivo(self):
        with self.assertRaises(ValidationError):
            self._criar_s1210(
                pagamento_ids=[
                    (
                        0,
                        0,
                        {
                            "dt_pgto": "2024-04-05",
                            "per_ref": "2024-03",
                            "ide_dm_dev": "DEM000001",
                            "vr_liq": 0.0,
                        },
                    )
                ]
            )

    def test_periodo_referencia_anual_aceito(self):
        """13º salário usa referência anual (AAAA)."""
        s1210 = self._criar_s1210(
            pagamento_ids=[
                (
                    0,
                    0,
                    {
                        "dt_pgto": "2024-12-20",
                        "per_ref": "2024",
                        "ide_dm_dev": "DEM000013",
                        "vr_liq": 1500.0,
                    },
                )
            ]
        )
        self.assertEqual(s1210.pagamento_ids.per_ref, "2024")

    def test_xml_contem_pagamento(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        payslip = self._criar_payslip(data_pagamento="2024-04-05")
        self._s1200_aceito(payslip)
        payslip.action_esocial_gerar_s1210()
        evento = payslip.l10n_br_esocial_s1210_id.evento_id
        self.assertEqual(evento.tipo, "S-1210")
        self.assertEqual(evento.per_apur, "2024-04")
        raiz = etree.fromstring(evento.xml_envio.encode("utf-8"))
        valores = {}
        for elemento in raiz.iter():
            tag = elemento.tag.rsplit("}", 1)[-1]
            valores.setdefault(tag, []).append((elemento.text or "").strip())
        self.assertEqual(valores["cpfBenef"], [self.cpf_employee])
        self.assertEqual(valores["perApur"], ["2024-04"])
        self.assertEqual(valores["perRef"], ["2024-03"])
        self.assertEqual(valores["dtPgto"], ["2024-04-05"])
        self.assertEqual(valores["vrLiq"], ["2584.80"])
