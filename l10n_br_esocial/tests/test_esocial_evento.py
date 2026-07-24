from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestESocialEvento(TransactionCase):
    """Testes da máquina de estados do evento eSocial."""

    def _create_evento(self, **kwargs):
        vals = {
            "tipo": "S-1200",
            "operacao": "I",
            "per_apur": "2024-01",
            "company_id": self.env.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.evento"].create(vals)

    def test_evento_default_state(self):
        """Evento novo deve ser criado em rascunho."""
        evento = self._create_evento()
        self.assertEqual(evento.state, "draft")

    def test_evento_validate(self):
        """Deve ser possível validar um evento em rascunho."""
        evento = self._create_evento()
        evento.action_validate()
        self.assertEqual(evento.state, "validated")

    def test_evento_validate_only_draft(self):
        """Só rascunhos podem ser validados."""
        evento = self._create_evento()
        evento.action_validate()
        with self.assertRaises(UserError):
            evento.action_validate()

    def test_evento_reset_draft_from_validated(self):
        """Evento validado pode voltar a rascunho."""
        evento = self._create_evento()
        evento.action_validate()
        evento.action_reset_draft()
        self.assertEqual(evento.state, "draft")

    def test_evento_reset_draft_from_error(self):
        """Evento com erro pode voltar a rascunho."""
        evento = self._create_evento()
        evento.action_mark_error()
        evento.action_reset_draft()
        self.assertEqual(evento.state, "draft")

    def test_evento_reset_draft_blocked(self):
        """Evento em sucesso não pode voltar a rascunho."""
        evento = self._create_evento()
        evento.action_mark_success()
        with self.assertRaises(UserError):
            evento.action_reset_draft()

    def test_evento_name_computation(self):
        """Nome deve conter o tipo do evento."""
        evento = self._create_evento(id_evento="ID1234")
        self.assertIn("S-1200", evento.name)
        self.assertIn("ID1234", evento.name)

    def test_evento_xml_fields(self):
        """Deve ser possível armazenar XML de envio e retorno."""
        evento = self._create_evento(
            xml_envio="<eSocial>test</eSocial>",
            xml_retorno="<retorno>ok</retorno>",
        )
        self.assertIn("eSocial", evento.xml_envio)
        self.assertIn("retorno", evento.xml_retorno)

    def test_evento_ocorrencias(self):
        """Deve ser possível adicionar ocorrências ao evento."""
        evento = self._create_evento()
        self.env["l10n_br.esocial.ocorrencia"].create(
            {
                "evento_id": evento.id,
                "codigo": "123",
                "descricao": "Campo obrigatório não informado",
                "tipo": "1",
            }
        )
        self.assertEqual(len(evento.ocorrencia_ids), 1)
        self.assertEqual(evento.ocorrencia_ids[0].tipo, "1")


class TestESocialLote(TransactionCase):
    """Testes do lote de transmissão eSocial."""

    def _create_evento(self, **kwargs):
        vals = {
            "tipo": "S-1200",
            "operacao": "I",
            "per_apur": "2024-01",
            "company_id": self.env.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.evento"].create(vals)

    def test_lote_default_state(self):
        """Lote novo deve ser criado em rascunho."""
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.env.company.id}
        )
        self.assertEqual(lote.state, "draft")

    def test_lote_add_validated_events(self):
        """Deve adicionar eventos validados sem lote."""
        evento1 = self._create_evento()
        evento1.action_validate()
        evento2 = self._create_evento(tipo="S-1010")
        evento2.action_validate()
        # Evento em draft não deve ser adicionado
        self._create_evento(tipo="S-1000")

        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.env.company.id}
        )
        lote.action_add_validated_events()
        self.assertEqual(lote.evento_count, 2)
        self.assertEqual(evento1.lote_id, lote)
        self.assertEqual(evento2.lote_id, lote)

    def test_lote_add_events_only_draft(self):
        """Só lotes em rascunho aceitam novos eventos."""
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.env.company.id}
        )
        lote.state = "sent"
        with self.assertRaises(UserError):
            lote.action_add_validated_events()

    def test_lote_reset_draft(self):
        """Lote enviado pode voltar a rascunho."""
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.env.company.id}
        )
        lote.state = "sent"
        lote.action_reset_draft()
        self.assertEqual(lote.state, "draft")

    def test_lote_name_with_protocolo(self):
        """Nome do lote deve conter protocolo quando disponível."""
        lote = self.env["l10n_br.esocial.lote"].create(
            {
                "company_id": self.env.company.id,
                "protocolo": "PROT123456",
            }
        )
        self.assertIn("PROT123456", lote.name)
