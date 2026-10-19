# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRequiredSupportDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create({"name": "Support Employee"})
        cls.required_type = cls._leave_type("Atestado", True, True)
        cls.optional_type = cls._leave_type("Folga com anexo opcional", True, False)
        cls.plain_type = cls._leave_type("Folga simples", False, False)

    @classmethod
    def _leave_type(cls, name, support_document, required):
        return cls.env["hr.leave.type"].create(
            {
                "name": name,
                "requires_allocation": "no",
                "leave_validation_type": "hr",
                "support_document": support_document,
                "required_support_document": required,
            }
        )

    def _vals(self, leave_type, day=2, **extra):
        vals = {
            "name": "Leave",
            "employee_id": self.employee.id,
            "holiday_status_id": leave_type.id,
            "date_from": datetime(2026, 3, day, 8, 0),
            "date_to": datetime(2026, 3, day, 17, 0),
            "request_date_from": "2026-03-%02d" % day,
            "request_date_to": "2026-03-%02d" % day,
        }
        vals.update(extra)
        return vals

    def _attachment(self):
        return self.env["ir.attachment"].create(
            {"name": "atestado.txt", "raw": b"atestado", "res_model": "hr.leave"}
        )

    def test_required_type_without_attachment_is_rejected(self):
        """
        Dado um tipo de folga que exige documento de suporte
        Quando a folga e criada sem anexo
        Entao ocorre ValidationError e a folga nao e gravada
        """
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(self._vals(self.required_type))
        self.assertFalse(
            self.env["hr.leave"].search(
                [("holiday_status_id", "=", self.required_type.id)]
            )
        )

    def test_required_type_with_attachment_is_accepted(self):
        """
        Dado um tipo de folga que exige documento de suporte
        Quando a folga e criada com um anexo
        Entao a folga e criada e o anexo fica vinculado a ela
        """
        attachment = self._attachment()
        leave = self.env["hr.leave"].create(
            self._vals(
                self.required_type,
                supported_attachment_ids=[(6, 0, attachment.ids)],
            )
        )
        self.assertEqual(leave.supported_attachment_ids, attachment)
        self.assertEqual(attachment.res_id, leave.id)

    def test_optional_type_without_attachment_is_accepted(self):
        """
        Dado um tipo com 'documento de suporte' mas sem obrigatoriedade
        Quando a folga e criada sem anexo
        Entao a folga e criada (a obrigatoriedade e um flag separado)
        """
        leave = self.env["hr.leave"].create(self._vals(self.optional_type, day=3))
        self.assertTrue(leave)
        self.assertFalse(leave.supported_attachment_ids)

    def test_plain_type_without_attachment_is_accepted(self):
        """
        Dado um tipo que nao exige documento
        Quando a folga e criada sem anexo
        Entao a folga e criada
        """
        leave = self.env["hr.leave"].create(self._vals(self.plain_type, day=4))
        self.assertTrue(leave)

    def test_batch_create_rejects_when_one_record_lacks_attachment(self):
        """
        Dado uma criacao em lote com uma folga comum e outra de tipo obrigatorio
        Quando o lote e criado e a segunda nao tem anexo
        Entao o lote inteiro falha com ValidationError
        """
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(
                [
                    self._vals(self.plain_type, day=5),
                    self._vals(self.required_type, day=6),
                ]
            )
        self.assertFalse(
            self.env["hr.leave"].search(
                [
                    ("employee_id", "=", self.employee.id),
                    ("holiday_status_id", "in", self.plain_type.ids),
                ]
            )
        )

    def test_default_of_required_flag_is_false(self):
        """
        Dado um tipo de folga novo
        Quando nada e informado
        Entao required_support_document e falso
        """
        leave_type = self.env["hr.leave.type"].create({"name": "Default"})
        self.assertFalse(leave_type.required_support_document)
        self.assertTrue(self.required_type.required_support_document)

    def test_form_view_exposes_flag_next_to_support_document(self):
        """
        Dado o formulario do tipo de folga
        Quando a view e montada
        Entao o campo required_support_document aparece logo apos support_document
        """
        arch = self.env["hr.leave.type"].get_view(
            self.env.ref("hr_holidays.edit_holiday_status_form").id, "form"
        )["arch"]
        self.assertIn("required_support_document", arch)
        self.assertLess(
            arch.index('name="support_document"'),
            arch.index('name="required_support_document"'),
        )
