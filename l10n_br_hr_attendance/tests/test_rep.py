# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes do cadastro de REP e da sequência de NSR (RP-01, RP-02)."""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import PontoCommon


@tagged("post_install", "-at_install")
class TestRep(PontoCommon):
    def test_rep_c_exige_numero_fabricacao(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.hr.rep"].create(
                {
                    "name": "Sem número",
                    "tipo": "rep_c",
                    "cnpj_cpf": "12.345.678/0001-95",
                }
            )

    def test_rep_p_exige_inpi(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_br.hr.rep"].create(
                {
                    "name": "Programa sem INPI",
                    "tipo": "rep_p",
                    "cnpj_cpf": "12.345.678/0001-95",
                }
            )

    def test_nsr_inicia_em_um_e_nao_tem_lacuna(self):
        """Anexo V: NSR sequencial, sem lacunas, iniciando em 1."""
        primeiro = self.rep._proximo_nsr()
        self.assertEqual(primeiro, [1])
        faixa = self.rep._proximo_nsr(3)
        self.assertEqual(faixa, [2, 3, 4])
        self.assertEqual(self.rep.nsr_ultimo, 4)

    def test_nsr_externo_avanca_contador(self):
        """AFD importado traz o NSR do relógio: o contador acompanha."""
        self.rep._registrar_nsr_externo(500)
        self.assertEqual(self.rep.nsr_ultimo, 500)
        self.assertEqual(self.rep._proximo_nsr(), [501])

    def test_nsr_externo_nao_retrocede(self):
        self.rep._registrar_nsr_externo(500)
        self.rep._registrar_nsr_externo(10)
        self.assertEqual(self.rep.nsr_ultimo, 500)

    def test_identificador_afd_por_tipo(self):
        self.assertEqual(self.rep._identificador_afd(), "12345678901234567")
        rep_p = self.env["l10n_br.hr.rep"].create(
            {
                "name": "REP-P KMEE",
                "tipo": "rep_p",
                "numero_inpi": "BR512024000123456",
                "cnpj_cpf": "12.345.678/0001-95",
            }
        )
        self.assertEqual(rep_p._identificador_afd(), "BR512024000123456")
        rep_a = self.env["l10n_br.hr.rep"].create(
            {
                "name": "REP-A do sindicato",
                "tipo": "rep_a",
                "cnpj_cpf": "12.345.678/0001-95",
            }
        )
        self.assertEqual(rep_a._identificador_afd(), "9" * 17)

    def test_atestado_vencido_bloqueia_uso(self):
        self.rep.write({"atestado_date_end": "2020-12-31"})
        self.assertFalse(self.rep.atestado_valido)
        with self.assertRaises(UserError):
            self.rep._check_atestado_vigente()

    def test_atestado_vigente_nao_bloqueia(self):
        self.assertTrue(self.rep.atestado_valido)
        self.rep._check_atestado_vigente()
