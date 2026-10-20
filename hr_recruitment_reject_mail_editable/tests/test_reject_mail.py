# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

EDITED = "Texto editado pelo recrutador QWERTY"
TEMPLATE_BODY = "Corpo original do modelo ZXCV"


@tagged("post_install", "-at_install")
class TestRejectMailEditable(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Recusa",
                "model_id": cls.env.ref("hr_recruitment.model_hr_applicant").id,
                "subject": "Sobre a sua candidatura",
                "body_html": "<p>%s</p>" % TEMPLATE_BODY,
                "email_to": "{{ object.email_from }}",
            }
        )
        cls.reason = cls.env["hr.applicant.refuse.reason"].create(
            {"name": "Perfil nao aderente", "template_id": cls.template.id}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Candidato Teste", "email": "candidato@example.com"}
        )
        # 18.0: nome e e-mail moram no hr.candidate, a candidatura aponta para ele
        cls.candidate = cls.env["hr.candidate"].create(
            {
                "partner_name": "Candidato Teste",
                "email_from": "candidato@example.com",
            }
        )
        cls.applicant = cls.env["hr.applicant"].create(
            {"candidate_id": cls.candidate.id}
        )

    def _wizard(self, **extra):
        vals = {
            "refuse_reason_id": self.reason.id,
            "applicant_ids": [(6, 0, self.applicant.ids)],
        }
        vals.update(extra)
        return self.env["applicant.get.refuse.reason"].create(vals)

    def _composer(self, wizard):
        action = wizard.action_open_selected_mail_template()
        composer = (
            self.env["mail.compose.message"]
            .with_context(mail_notify_force_send=False, **action["context"])
            .create({})
        )
        # destinatario explicito: sem ele o composer nao enfileira e-mail
        composer.partner_ids = self.partner
        return composer

    def _messages(self, text):
        return self.applicant.message_ids.filtered(lambda m: text in (m.body or ""))

    def _mails(self, text):
        """Fila de e-mails (mail.mail): o fluxo de recusa do core apaga a
        mensagem do chatter (auto_delete_message), mas o e-mail enfileirado fica."""
        return self.env["mail.mail"].search([("body_html", "ilike", text)])

    def test_refuse_opens_composer_when_mail_is_to_be_sent(self):
        """
        Dado um motivo de recusa com modelo de e-mail
        Quando o botao Refuse do wizard e acionado
        Entao abre o compositor de e-mail com o modelo e o candidato
        """
        wizard = self._wizard()
        self.assertTrue(wizard.send_mail)
        action = wizard.action_open_selected_mail_template()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(action["target"], "new")
        context = action["context"]
        self.assertEqual(context["default_model"], "hr.applicant")
        self.assertEqual(context["default_res_ids"], self.applicant.ids)
        self.assertEqual(context["default_template_id"], self.template.id)
        self.assertEqual(context["refuse_reason_wizard_id"], wizard.id)

    def test_refuse_does_nothing_when_mail_is_off(self):
        """
        Dado um wizard com 'enviar e-mail' desligado
        Quando action_open_selected_mail_template e chamada
        Entao nada abre (o botao padrao de recusa e que atua)
        """
        wizard = self._wizard(send_mail=False)
        self.assertFalse(wizard.action_open_selected_mail_template())

    def test_refuse_does_nothing_without_template(self):
        """
        Dado um wizard com 'enviar e-mail' mas sem modelo
        Quando action_open_selected_mail_template e chamada
        Entao nada abre
        """
        wizard = self._wizard(send_mail=True, template_id=False)
        self.assertFalse(wizard.action_open_selected_mail_template())

    def test_sending_edited_mail_refuses_the_applicant(self):
        """
        Dado o compositor aberto pelo wizard de recusa
        Quando o recrutador edita o texto e envia
        Entao o candidato e recusado (arquivado, com o motivo)
        """
        wizard = self._wizard()
        composer = self._composer(wizard)
        composer.body = "<p>%s</p>" % EDITED
        composer.action_send_mail()
        self.assertFalse(self.applicant.active)
        self.assertEqual(self.applicant.refuse_reason_id, self.reason)

    def test_edited_text_is_what_gets_sent(self):
        """
        Dado o compositor com o corpo editado
        Quando o e-mail e enviado
        Entao o candidato recebe o texto editado
        """
        wizard = self._wizard()
        composer = self._composer(wizard)
        composer.body = "<p>%s</p>" % EDITED
        composer.action_send_mail()
        self.assertEqual(len(self._mails(EDITED)), 1)

    def test_original_template_is_not_sent_in_addition(self):
        """
        Dado o compositor com o corpo editado
        Quando o e-mail e enviado e a recusa aplicada
        Entao o modelo original NAO e enviado de novo (sem e-mail duplicado)
        """
        wizard = self._wizard()
        composer = self._composer(wizard)
        composer.body = "<p>%s</p>" % EDITED
        composer.action_send_mail()
        self.assertFalse(self._mails(TEMPLATE_BODY))
        self.assertFalse(self._messages(TEMPLATE_BODY))

    def test_compose_outside_the_refuse_flow_does_not_refuse(self):
        """
        Dado um compositor sobre o candidato aberto fora do wizard de recusa
        Quando um e-mail e enviado
        Entao o candidato continua ativo e sem motivo de recusa
        """
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model="hr.applicant", default_res_ids=self.applicant.ids
            )
            .create({"subject": "Oi", "body": "<p>Ola</p>"})
        )
        composer.action_send_mail()
        self.assertTrue(self.applicant.active)
        self.assertFalse(self.applicant.refuse_reason_id)

    def test_wizard_view_swaps_apply_button(self):
        """
        Dado o formulario do wizard de recusa
        Quando a view e montada
        Entao o botao Refuse chama action_open_selected_mail_template
        """
        arch = self.env["applicant.get.refuse.reason"].get_view(
            self.env.ref("hr_recruitment.applicant_get_refuse_reason_view_form").id,
            "form",
        )["arch"]
        self.assertIn("action_open_selected_mail_template", arch)
