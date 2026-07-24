# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestESocialTabelas(TransactionCase):
    """Testes das tabelas de referência do eSocial."""

    def test_natureza_rubrica_loaded(self):
        """Tabela 3 deve ter ao menos 150 registros carregados."""
        count = self.env["l10n_br.esocial.natureza.rubrica"].search_count(
            [("active", "in", (True, False))]
        )
        self.assertGreater(count, 150)

    def test_natureza_rubrica_salario(self):
        """Código 1000 deve ser Salário."""
        rec = self.env.ref("l10n_br_esocial.nat_rubr_1000")
        self.assertEqual(rec.codigo, "1000")
        self.assertIn("alário", rec.nome)
        self.assertIn("1000", rec.name)

    def test_natureza_rubrica_inss(self):
        """Código 9201 deve ser Contribuição Previdenciária."""
        rec = self.env.ref("l10n_br_esocial.nat_rubr_9201")
        self.assertEqual(rec.codigo, "9201")
        self.assertIn("previdenci", rec.nome.lower())

    def test_natureza_rubrica_irrf(self):
        """Código 9203 deve ser IRRF."""
        rec = self.env.ref("l10n_br_esocial.nat_rubr_9203")
        self.assertEqual(rec.codigo, "9203")

    def test_categoria_trabalhador_loaded(self):
        """Tabela 1 deve ter ao menos 30 registros."""
        count = self.env["l10n_br.esocial.categoria.trabalhador"].search_count(
            [("active", "in", (True, False))]
        )
        self.assertGreater(count, 30)

    def test_categoria_trabalhador_clt(self):
        """Código 101 deve ser Empregado CLT."""
        rec = self.env.ref("l10n_br_esocial.cat_trab_101")
        self.assertEqual(rec.codigo, "101")
        self.assertEqual(rec.grupo, "SE")
        self.assertIn("CLT", rec.nome)

    def test_classificacao_tributaria_loaded(self):
        """Tabela 8 deve ter ao menos 15 registros."""
        count = self.env["l10n_br.esocial.classificacao.tributaria"].search_count([])
        self.assertGreater(count, 15)

    def test_classificacao_tributaria_geral(self):
        """Código 99 deve ser Pessoas Jurídicas em Geral."""
        recs = self.env["l10n_br.esocial.classificacao.tributaria"].search(
            [("codigo", "=", "99")]
        )
        self.assertEqual(len(recs), 1)
        self.assertIn("geral", recs.nome.lower())

    def test_lotacao_tributaria_loaded(self):
        """Tabela 10 deve ter ao menos 10 registros."""
        count = self.env["l10n_br.esocial.lotacao.tributaria"].search_count([])
        self.assertGreater(count, 10)

    def test_motivo_afastamento_loaded(self):
        """Tabela 18 deve ter ao menos 25 registros."""
        count = self.env["l10n_br.esocial.motivo.afastamento"].search_count([])
        self.assertGreater(count, 25)

    def test_motivo_afastamento_maternidade(self):
        """Código 17 deve ser Licença Maternidade."""
        rec = self.env.ref("l10n_br_esocial.mot_afast_17")
        self.assertEqual(rec.codigo, "17")
        self.assertIn("maternidade", rec.nome.lower())

    def test_motivo_desligamento_loaded(self):
        """Tabela 19 deve ter ao menos 30 registros."""
        count = self.env["l10n_br.esocial.motivo.desligamento"].search_count([])
        self.assertGreater(count, 30)

    def test_motivo_desligamento_justa_causa(self):
        """Código 01 deve ser Rescisão com justa causa."""
        rec = self.env.ref("l10n_br_esocial.mot_deslig_01")
        self.assertEqual(rec.codigo, "01")
        self.assertIn("justa causa", rec.nome)

    def test_motivo_desligamento_sem_justa_causa(self):
        """Código 02 deve ser Rescisão sem justa causa."""
        rec = self.env.ref("l10n_br_esocial.mot_deslig_02")
        self.assertEqual(rec.codigo, "02")
        self.assertIn("sem justa causa", rec.nome)
