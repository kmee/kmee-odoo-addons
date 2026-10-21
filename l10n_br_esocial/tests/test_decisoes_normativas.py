# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

BASE = "l10n_br.esocial.base.intermediario"


@tagged("post_install", "-at_install")
class TestDecisoesNormativas(TransactionCase):
    """Decisões normativas de 19/10/2026: multiempresa e números de tabela."""

    def _intermediarios(self):
        base = self.env.registry[BASE]
        return [
            nome
            for nome, modelo in self.env.registry.items()
            if nome != BASE
            and issubclass(modelo, base)
            and not modelo._abstract
            and not modelo._transient
        ]

    def _regra_multiempresa(self, nome_modelo):
        return (
            self.env["ir.rule"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("model_id.model", "=", nome_modelo),
                    ("global", "=", True),
                    ("domain_force", "ilike", "company_ids"),
                ]
            )
        )

    # ── Multiempresa por padrão (LGPD, art. 46) ─────────────────────────────

    def test_todo_intermediario_tem_regra_multiempresa(self):
        """Todo modelo que herda o intermediário nasce com a regra."""
        nomes = self._intermediarios()
        self.assertTrue(nomes)
        for nome in nomes:
            self.assertTrue(self._regra_multiempresa(nome), nome)

    def test_regra_e_recriada_para_intermediario_sem_regra(self):
        self._regra_multiempresa("l10n_br.esocial.s2230").unlink()
        self.env[BASE]._l10n_br_esocial_garantir_regras_multiempresa()
        self.assertTrue(self._regra_multiempresa("l10n_br.esocial.s2230"))

    def test_regra_desativada_nao_e_recriada(self):
        """Quem desativa a regra de propósito não a vê voltar sozinha."""
        regra = self._regra_multiempresa("l10n_br.esocial.s2230")
        regra.active = False
        self.env[BASE]._l10n_br_esocial_garantir_regras_multiempresa()
        self.assertEqual(self._regra_multiempresa("l10n_br.esocial.s2230"), regra)

    # ── Números de tabela (Anexo I do leiaute S-1.3, de 01 a 30) ────────────

    def test_numeros_de_tabela_corrigidos(self):
        nome = lambda modelo: self.env["ir.model"]._get(modelo).name  # noqa: E731
        self.assertIn("Tabela 24", nome("l10n_br.esocial.agente.nocivo"))
        self.assertIn("Tabela 07", nome("l10n_br.esocial.tipo.dependente"))
        self.assertIn("Tabela 22", nome("l10n_br.esocial.compat.fpas"))
        self.assertIn("Tabela 25", nome("l10n_br.esocial.tipo.beneficio"))
        self.assertIn("Tabela 26", nome("l10n_br.esocial.motivo.cessacao"))
        self.assertIn("Tabela 28", nome("l10n_br.esocial.treinamento"))
        self.assertIn("Tabela 29", nome("l10n_br.esocial.receita.reclamatoria"))
        self.assertNotIn("Tab", nome("l10n_br.esocial.aposentadoria.especial"))

    def test_nenhuma_tabela_fora_do_anexo_i(self):
        """O Anexo I vai de 01 a 30: número acima disso não existe."""
        padrao = re.compile(r"\bTab(?:ela|\.)?\s*(\d+)\b")
        modelos = self.env["ir.model"].search([("model", "like", "l10n_br.esocial.")])
        menus = self.env["ir.ui.menu"].search([("name", "like", "Tab")])
        for rotulo in modelos.mapped("name") + menus.mapped("name"):
            for numero in padrao.findall(rotulo):
                self.assertLessEqual(int(numero), 30, rotulo)

    def test_feriados_padrao_so_nacionais(self):
        """Carnaval, Paixão e Corpus Christi não são feriados nacionais."""
        feriados = self.env["l10n_br.esocial.feriado"].search(
            [("nome", "in", ("Carnaval", "Sexta-feira da Paixão", "Corpus Christi"))]
        )
        self.assertFalse(feriados)
