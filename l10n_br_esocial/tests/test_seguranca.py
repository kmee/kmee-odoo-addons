# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestSegurancaEventos(ESocialCicloCommon):
    """Eventos carregam CPF e remuneração: acesso restrito à folha."""

    def setUp(self):
        super().setUp()
        self.evento = self._criar_evento("S-1200", per_apur="2024-03")

    def test_usuario_interno_comum_nao_le_evento(self):
        comum = new_test_user(self.env, login="esocial_comum", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["l10n_br.esocial.evento"].with_user(comum).search([])

    def test_usuario_de_folha_le_evento(self):
        folha = new_test_user(
            self.env,
            login="esocial_folha",
            groups="base.group_user,payroll.group_payroll_user",
        )
        eventos = self.env["l10n_br.esocial.evento"].with_user(folha).search([])
        self.assertIn(self.evento, eventos)
        with self.assertRaises(AccessError):
            self.evento.with_user(folha).write({"per_apur": "2024-04"})

    def test_evento_de_outra_empresa_fica_oculto(self):
        outra = self.env["res.company"].create({"name": "Outra Empresa eSocial"})
        alheio = self._criar_evento("S-1200", per_apur="2024-03", company_id=outra.id)
        folha = new_test_user(
            self.env,
            login="esocial_folha2",
            groups="base.group_user,payroll.group_payroll_user",
            company_id=self.company.id,
            company_ids=[(6, 0, [self.company.id])],
        )
        eventos = self.env["l10n_br.esocial.evento"].with_user(folha).search([])
        self.assertIn(self.evento, eventos)
        self.assertNotIn(alheio, eventos)
