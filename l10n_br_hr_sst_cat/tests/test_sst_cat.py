# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon


@tagged("post_install", "-at_install")
class TestSstCat(SstCommon):
    """RS-12 e RS-13: acidente, CAT, prazo legal e afastamento."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.situacao = cls.env["l10n_br.esocial.situacao.geradora"].search([], limit=1)
        cls.parte_corpo = cls.env["l10n_br.esocial.parte.corpo"].search([], limit=1)
        cls.agente_causador = cls.env["l10n_br.esocial.agente.causador"].search(
            [], limit=1
        )

    def _cria_acidente(self, **kwargs):
        valores = {
            "employee_id": self.employee.id,
            # Quarta-feira, para que o dia útil seguinte seja quinta.
            "date_acidente": date(2026, 6, 10),
            "hora_acidente": "1430",
            "tp_acid": "1",
            "situacao_geradora_id": self.situacao.id,
            "parte_corpo_id": self.parte_corpo.id,
            "agente_causador_id": self.agente_causador.id,
        }
        valores.update(kwargs)
        return self.env["l10n_br.sst.acidente"].create(valores)

    # ── Acidente ────────────────────────────────────────────────────────────

    def test_hora_invalida(self):
        with self.assertRaises(ValidationError):
            self._cria_acidente(hora_acidente="25:00")

    def test_obito_exige_data(self):
        with self.assertRaises(ValidationError):
            self._cria_acidente(houve_obito=True)

    def test_obito_anterior_ao_acidente(self):
        with self.assertRaises(ValidationError):
            self._cria_acidente(houve_obito=True, date_obito=date(2026, 6, 9))

    def test_registrar_abre_cat_inicial(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        self.assertEqual(acidente.state, "registrado")
        self.assertEqual(len(acidente.cat_ids), 1)
        self.assertEqual(acidente.cat_ids.tipo_cat_codigo, "1")

    def test_reabertura_vincula_a_cat_inicial(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        inicial = acidente.cat_ids
        reabertura = acidente.action_criar_cat_reabertura()
        self.assertEqual(reabertura.cat_origem_id, inicial)

    def test_reabertura_sem_cat_inicial(self):
        """Reabrir o que nunca foi comunicado não faz sentido nem no leiaute."""
        acidente = self._cria_acidente()
        with self.assertRaises(UserError):
            acidente.action_criar_cat_reabertura()

    def test_cat_de_obito_exige_obito(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        with self.assertRaises(UserError):
            acidente.action_criar_cat_obito()

    # ── Prazo legal (art. 22 da Lei 8.213/91) ───────────────────────────────

    def test_prazo_e_o_primeiro_dia_util_seguinte(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        self.assertEqual(acidente.cat_ids.date_limite, date(2026, 6, 11))

    def test_prazo_pula_o_fim_de_semana(self):
        """Acidente na sexta: o prazo cai na segunda-feira."""
        acidente = self._cria_acidente(date_acidente=date(2026, 6, 12))
        acidente.action_registrar()
        self.assertEqual(acidente.cat_ids.date_limite, date(2026, 6, 15))

    def test_prazo_de_obito_e_imediato(self):
        acidente = self._cria_acidente(houve_obito=True, date_obito=date(2026, 6, 10))
        acidente.action_registrar()
        self.assertEqual(acidente.cat_ids.date_limite, date(2026, 6, 10))

    def test_emissao_fora_do_prazo_registra_no_chatter(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        cat = acidente.cat_ids
        cat.date_emissao = date(2026, 6, 20)
        mensagens_antes = len(cat.message_ids)
        cat.action_emitir()
        self.assertEqual(cat.prazo_situacao, "atrasada")
        self.assertGreater(len(cat.message_ids), mensagens_antes)

    def test_emissao_no_prazo(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        cat = acidente.cat_ids
        cat.date_emissao = date(2026, 6, 11)
        cat.action_emitir()
        self.assertEqual(cat.prazo_situacao, "hoje")
        self.assertEqual(acidente.state, "comunicado")

    def test_cron_alerta_prazo(self):
        acidente = self._cria_acidente()
        acidente.action_registrar()
        cat = acidente.cat_ids
        pendentes = self.env["l10n_br.sst.cat"].cron_alerta_prazo()
        self.assertIn(cat, pendentes)

    # ── Afastamento (RS-13) ─────────────────────────────────────────────────

    def test_afastamento_exige_marcacao(self):
        acidente = self._cria_acidente()
        with self.assertRaises(UserError):
            acidente.action_gerar_afastamento()

    def test_afastamento_usa_motivo_de_acidente_do_trabalho(self):
        acidente = self._cria_acidente(
            houve_afastamento=True, ultimo_dia_trabalhado=date(2026, 6, 10)
        )
        afastamento = acidente.action_gerar_afastamento()
        self.assertEqual(afastamento.cod_mot_afast, "01")
        self.assertEqual(afastamento.employee_id, self.employee)
        self.assertEqual(acidente.afastamento_id, afastamento)

    def test_afastamento_nao_duplica(self):
        acidente = self._cria_acidente(houve_afastamento=True)
        primeiro = acidente.action_gerar_afastamento()
        segundo = acidente.action_gerar_afastamento()
        self.assertEqual(primeiro, segundo)

    def test_doenca_ocupacional_tambem_e_acidente_do_trabalho(self):
        """Doença ocupacional não vira 'não relacionada ao trabalho'."""
        acidente = self._cria_acidente(tp_acid="2", houve_afastamento=True)
        afastamento = acidente.action_gerar_afastamento()
        self.assertEqual(afastamento.cod_mot_afast, "01")

    def test_contador_no_empregado(self):
        self._cria_acidente()
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.l10n_br_sst_acidente_count, 1)
