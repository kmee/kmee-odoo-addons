# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon


@tagged("post_install", "-at_install")
class TestSstEpi(SstCommon):
    """RS-05 a RS-08: Certificado de Aprovação, entrega e ficha de EPI."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hoje = fields.Date.context_today(cls.env["l10n_br.sst.ca"])
        cls.ca_valido = cls.env["l10n_br.sst.ca"].create(
            {
                "numero": "12345",
                "descricao_epi": "Protetor auricular tipo concha",
                "tipo_epi": "Protetor auditivo",
                "validade": cls.hoje + relativedelta(years=2),
                "risco_neutralizado_ids": [(6, 0, [cls.risco.id])],
            }
        )
        cls.ca_vencido = cls.env["l10n_br.sst.ca"].create(
            {
                "numero": "99999",
                "descricao_epi": "Protetor auricular de inserção",
                "validade": cls.hoje - relativedelta(days=1),
                "risco_neutralizado_ids": [(6, 0, [cls.risco.id])],
            }
        )
        cls.produto = cls.env["product.product"].create(
            {
                "name": "Protetor Auricular",
                "type": "consu",
                "is_personal_equipment": True,
                "is_ppe": True,
                "l10n_br_sst_ca_id": cls.ca_valido.id,
            }
        )

    def _cria_entrega(self, ca=None, start_date=None):
        request = self.env["hr.personal.equipment.request"].create(
            {
                "employee_id": self.employee.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.produto.id,
                            "quantity": 1,
                            "start_date": start_date or self.hoje,
                            "l10n_br_sst_ca_id": (ca or self.ca_valido).id,
                        },
                    )
                ],
            }
        )
        request.accept_request()
        return request.line_ids

    # ── Certificado de Aprovação ────────────────────────────────────────────

    def test_ca_state_vigente(self):
        self.assertEqual(self.ca_valido.state, "vigente")
        self.assertEqual(self.ca_vencido.state, "vencido")

    def test_ca_state_a_vencer(self):
        ca = self.env["l10n_br.sst.ca"].create(
            {
                "numero": "55555",
                "descricao_epi": "Luva de raspa",
                "validade": self.hoje + relativedelta(days=10),
            }
        )
        self.assertEqual(ca.state, "a_vencer")

    def test_ca_numero_unico(self):
        from psycopg2 import IntegrityError

        from odoo.tools import mute_logger

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["l10n_br.sst.ca"].create(
                    {
                        "numero": "12345",
                        "descricao_epi": "Duplicado",
                        "validade": self.hoje,
                    }
                )

    def test_ca_agentes_nocivos_derivados_do_risco(self):
        self.assertIn(self.agente_ruido, self.ca_valido.agente_nocivo_ids)

    def test_ca_vigente_em(self):
        self.assertTrue(self.ca_valido._vigente_em(self.hoje))
        self.assertFalse(self.ca_vencido._vigente_em(self.hoje))

    # ── Entrega ─────────────────────────────────────────────────────────────

    def test_entrega_preenche_certification_com_o_ca(self):
        entrega = self._cria_entrega()
        self.assertEqual(entrega.certification, "12345")

    def test_entrega_com_ca_vencido_e_bloqueada(self):
        entrega = self._cria_entrega(ca=self.ca_vencido)
        with self.assertRaises(UserError):
            entrega.validate_allocation()

    def test_entrega_sem_ca_e_bloqueada(self):
        entrega = self._cria_entrega()
        entrega.l10n_br_sst_ca_id = False
        with self.assertRaises(UserError):
            entrega.validate_allocation()

    def test_entrega_com_ca_valido_passa(self):
        entrega = self._cria_entrega()
        entrega.validate_allocation()
        self.assertEqual(entrega.state, "valid")

    def test_ca_vence_depois_da_entrega_nao_bloqueia_o_passado(self):
        """O que importa é a validade do CA na data da entrega."""
        ca = self.env["l10n_br.sst.ca"].create(
            {
                "numero": "77777",
                "descricao_epi": "Óculos de proteção",
                "validade": self.hoje - relativedelta(days=10),
            }
        )
        entrega = self._cria_entrega(
            ca=ca, start_date=self.hoje - relativedelta(days=30)
        )
        entrega.validate_allocation()
        self.assertEqual(entrega.state, "valid")

    # ── Assinatura e devolução ──────────────────────────────────────────────

    def test_assinatura_exige_imagem(self):
        entrega = self._cria_entrega()
        with self.assertRaises(UserError):
            entrega.action_assinar()

    def test_assinatura_carimba_data(self):
        entrega = self._cria_entrega()
        entrega.l10n_br_sst_assinatura = b"YXNzaW5hdHVyYQ=="
        entrega.action_assinar()
        self.assertTrue(entrega.l10n_br_sst_data_assinatura)

    def test_devolucao_exige_motivo(self):
        entrega = self._cria_entrega()
        entrega.validate_allocation()
        with self.assertRaises(UserError):
            entrega.action_devolver()

    def test_devolucao_expira_a_entrega(self):
        entrega = self._cria_entrega()
        entrega.validate_allocation()
        entrega.l10n_br_sst_motivo_devolucao = "troca"
        entrega.action_devolver()
        self.assertEqual(entrega.state, "expired")
        self.assertTrue(entrega.l10n_br_sst_data_devolucao)

    # ── Consulta usada pelo S-2240 ──────────────────────────────────────────

    def test_epis_do_risco(self):
        entrega = self._cria_entrega()
        entrega.validate_allocation()
        encontradas = self.employee._l10n_br_sst_epis_do_risco(self.risco, self.hoje)
        self.assertIn(entrega, encontradas)

    def test_epi_devolvido_sai_da_consulta(self):
        entrega = self._cria_entrega()
        entrega.validate_allocation()
        entrega.write(
            {
                "l10n_br_sst_motivo_devolucao": "desligamento",
                "l10n_br_sst_data_devolucao": self.hoje - relativedelta(days=1),
            }
        )
        encontradas = self.employee._l10n_br_sst_epis_do_risco(self.risco, self.hoje)
        self.assertNotIn(entrega, encontradas)

    def test_cron_alerta_vencimento(self):
        entrega = self._cria_entrega(ca=self.ca_vencido)
        entrega.state = "valid"
        mensagens_antes = len(self.ca_vencido.message_ids)
        self.env["l10n_br.sst.ca"].cron_alerta_vencimento()
        self.assertGreater(len(self.ca_vencido.message_ids), mensagens_antes)
