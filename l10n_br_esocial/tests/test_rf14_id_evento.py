# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from unittest import mock

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    import esociallib  # noqa: F401

    HAS_ESOCIALLIB = True
except ImportError:
    HAS_ESOCIALLIB = False


class _FakeEventoResult:
    # __slots__ mantém a classe leve e satisfaz o flake8-bugbear B903.
    __slots__ = ("event_id", "aceito", "nr_recibo", "code", "description")

    def __init__(self, event_id, aceito=True, nr_recibo=None, code=None, desc=None):
        self.event_id = event_id
        self.aceito = aceito
        self.nr_recibo = nr_recibo
        self.code = code
        self.description = desc


class _FakeLoteResult:
    def __init__(self, status="processado", eventos=None):
        self.status = status
        self.eventos = eventos or []


class TestRF14IdEvento(TransactionCase):
    """RF-14: id_evento deve ser preenchido na geração e casar no retorno."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        partner = cls.company.partner_id
        if not partner.cnpj_cpf:
            partner.write({"cnpj_cpf": "02.546.716/0001-46"})
        cls.class_trib = cls.env.ref("l10n_br_esocial.class_trib_01")
        cls.company.write({"l10n_br_esocial_class_trib_id": cls.class_trib.id})

    # ── _extract_id_evento (unit, sem esociallib) ──────────────────────────

    def test_extract_id_evento_from_xml(self):
        """Deve extrair o atributo Id do elemento-evento (filho de eSocial)."""
        base = self.env["l10n_br.esocial.base.intermediario"]
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtRemun/'
            'v_S_01_03_00">'
            '<evtRemun Id="ID1123456780000002024031512300000001">'
            "<ideEvento/></evtRemun></eSocial>"
        )
        self.assertEqual(
            base._extract_id_evento(xml),
            "ID1123456780000002024031512300000001",
        )

    def test_extract_id_evento_invalid_xml(self):
        """XML inválido/ausente deve retornar False (nunca levantar)."""
        base = self.env["l10n_br.esocial.base.intermediario"]
        self.assertFalse(base._extract_id_evento("not xml <<<"))
        self.assertFalse(base._extract_id_evento(""))
        self.assertFalse(base._extract_id_evento(False))

    # ── geração preenche id_evento (requer esociallib) ─────────────────────

    def test_gerar_evento_preenche_id_evento(self):
        """action_gerar_evento deve preencher id_evento com o Id do XML."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        s1000 = self.env["l10n_br.esocial.s1000"].create(
            {
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        evento = s1000.action_gerar_evento()
        self.assertTrue(evento.id_evento, "id_evento deve estar preenchido")
        self.assertEqual(len(evento.id_evento), 36)
        self.assertTrue(evento.id_evento.startswith("ID"))
        # O id_evento deve bater exatamente com o Id presente no XML gerado.
        id_from_xml = self.env["l10n_br.esocial.base.intermediario"]._extract_id_evento(
            evento.xml_envio
        )
        self.assertEqual(evento.id_evento, id_from_xml)

    # ── matching do retorno casa pelo id_evento ────────────────────────────

    def test_retorno_casa_por_id_evento_aceito(self):
        """Retorno com event_id igual ao id_evento deve casar e criar recibo."""
        evento = self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": "S-1200",
                "operacao": "I",
                "id_evento": "ID1123456780000002024031512300000001",
                "state": "sent",
                "company_id": self.company.id,
            }
        )
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.company.id, "protocolo": "PROT-1"}
        )
        evento.lote_id = lote.id

        fake = _FakeLoteResult(
            eventos=[
                _FakeEventoResult(
                    event_id="ID1123456780000002024031512300000001",
                    aceito=True,
                    nr_recibo="1.2.202403.0000001",
                )
            ]
        )
        with mock.patch(
            "odoo.addons.l10n_br_esocial.models.esocial_lote.consultar_lote",
            return_value=fake,
        ), mock.patch.object(type(lote), "_get_certificate", return_value=(b"", "")):
            lote.action_consultar()

        self.assertEqual(evento.state, "success")
        self.assertEqual(evento.nr_recibo, "1.2.202403.0000001")
        self.assertEqual(lote.state, "done")

    def test_retorno_rejeitado_cria_ocorrencia(self):
        """Retorno rejeitado deve marcar erro e criar ocorrência."""
        evento = self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": "S-1200",
                "operacao": "I",
                "id_evento": "ID9999",
                "state": "sent",
                "company_id": self.company.id,
            }
        )
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.company.id, "protocolo": "PROT-2"}
        )
        evento.lote_id = lote.id
        fake = _FakeLoteResult(
            eventos=[
                _FakeEventoResult(
                    event_id="ID9999",
                    aceito=False,
                    code="301",
                    desc="Erro de validação",
                )
            ]
        )
        with mock.patch(
            "odoo.addons.l10n_br_esocial.models.esocial_lote.consultar_lote",
            return_value=fake,
        ), mock.patch.object(type(lote), "_get_certificate", return_value=(b"", "")):
            lote.action_consultar()

        self.assertEqual(evento.state, "error")
        self.assertEqual(lote.state, "error")
        self.assertEqual(len(evento.ocorrencia_ids), 1)
        self.assertEqual(evento.ocorrencia_ids.codigo, "301")

    def test_retorno_id_nao_casa_nao_altera_evento(self):
        """event_id que não casa não deve alterar nenhum evento."""
        evento = self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": "S-1200",
                "operacao": "I",
                "id_evento": "ID-CORRETO",
                "state": "sent",
                "company_id": self.company.id,
            }
        )
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.company.id, "protocolo": "PROT-3"}
        )
        evento.lote_id = lote.id
        fake = _FakeLoteResult(
            eventos=[_FakeEventoResult(event_id="ID-DIFERENTE", aceito=True)]
        )
        with mock.patch(
            "odoo.addons.l10n_br_esocial.models.esocial_lote.consultar_lote",
            return_value=fake,
        ), mock.patch.object(type(lote), "_get_certificate", return_value=(b"", "")):
            lote.action_consultar()

        self.assertEqual(evento.state, "sent")
        self.assertFalse(evento.nr_recibo)


class TestRF25LoteHomogeneidade(TransactionCase):
    """RF-25: lote deve ser homogêneo por grupo eSocial."""

    def setUp(self):
        super().setUp()
        self.lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.env.company.id}
        )

    def _evento(self, tipo):
        return self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": tipo,
                "operacao": "I",
                "state": "validated",
                "company_id": self.env.company.id,
                "lote_id": self.lote.id,
            }
        )

    def test_classify_grupo(self):
        self.assertEqual(self.lote._classify_grupo("S-1000"), 1)
        self.assertEqual(self.lote._classify_grupo("S-1010"), 1)
        self.assertEqual(self.lote._classify_grupo("S-2200"), 2)
        self.assertEqual(self.lote._classify_grupo("S-3000"), 2)
        self.assertEqual(self.lote._classify_grupo("S-1200"), 3)
        self.assertEqual(self.lote._classify_grupo("S-1299"), 3)

    def test_lote_homogeneo_ok(self):
        eventos = self._evento("S-1000") + self._evento("S-1010")
        self.assertEqual(self.lote._get_lote_grupo(eventos), 1)

    def test_lote_grupos_mistos_bloqueia(self):
        eventos = self._evento("S-1010") + self._evento("S-1200")
        with self.assertRaises(UserError):
            self.lote._get_lote_grupo(eventos)


class TestRF25AuditoriaGuarda(TransactionCase):
    """RF-25: forçar estado exige grupo manager e registra no chatter."""

    def setUp(self):
        super().setUp()
        self.evento = self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": "S-1200",
                "operacao": "I",
                "company_id": self.env.company.id,
            }
        )
        self.manager_group = self.env.ref("payroll.group_payroll_manager")

    def test_mark_success_sem_grupo_bloqueia(self):
        user = self.env["res.users"].create(
            {
                "name": "eSocial User",
                "login": "esocial_user_no_mgr",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(UserError):
            self.evento.with_user(user).action_mark_success()

    def test_mark_success_com_grupo_registra_chatter(self):
        self.env.user.groups_id = [(4, self.manager_group.id)]
        n_before = len(self.evento.message_ids)
        self.evento.action_mark_success()
        self.assertEqual(self.evento.state, "success")
        self.assertGreater(len(self.evento.message_ids), n_before)

    def test_mark_error_com_grupo_registra_chatter(self):
        self.env.user.groups_id = [(4, self.manager_group.id)]
        n_before = len(self.evento.message_ids)
        self.evento.action_mark_error()
        self.assertEqual(self.evento.state, "error")
        self.assertGreater(len(self.evento.message_ids), n_before)
