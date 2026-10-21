# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import patch

from odoo import api
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.mail.models.mail_thread import MailThread

FLAG = "mail_auto_subscribe_no_notify"


@tagged("post_install", "-at_install")
class TestHolidaysNoMail(TransactionCase):
    """O modulo suprime o aviso de auto-assinatura (mail_auto_subscribe_no_notify)
    no create/write de hr.leave e hr.leave.allocation. O teste espia o
    mail.thread.create/write (fim da cadeia de heranca) e le o contexto que
    chegou la."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create({"name": "No Mail Employee"})
        cls.leave_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "No Mail Leave",
                "code": "NOMAILLEAVE",
                "count_as": "absence",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        cls.alloc_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "No Mail Allocation",
                "code": "NOMAILALLOC",
                "count_as": "absence",
                "requires_allocation": True,
                "employee_requests": False,
                "allocation_validation_type": "hr",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )

    def _leave_vals(self):
        return {
            "name": "Leave",
            "employee_id": self.employee.id,
            "work_entry_type_id": self.leave_type.id,
            "date_from": datetime(2026, 3, 2, 8, 0),
            "date_to": datetime(2026, 3, 3, 17, 0),
            "request_date_from": "2026-03-02",
            "request_date_to": "2026-03-03",
        }

    def _allocation_vals(self):
        return {
            "name": "Allocation",
            "work_entry_type_id": self.alloc_type.id,
            "employee_id": self.employee.id,
            "number_of_days": 3,
        }

    def _spy(self, method):
        """Registra (modelo, valor do flag) a cada create/write de mail.thread."""
        seen = []
        original = getattr(MailThread, method)

        if method == "create":

            @api.model_create_multi
            def spy(model, vals_list):
                seen.append((model._name, model.env.context.get(FLAG)))
                return original(model, vals_list)

        else:

            def spy(model, vals):
                seen.append((model._name, model.env.context.get(FLAG)))
                return original(model, vals)

        return seen, patch.object(MailThread, method, spy)

    def _flags(self, seen, model):
        return [flag for name, flag in seen if name == model]

    def test_leave_create_suppresses_auto_subscribe_notification(self):
        """
        Dado um funcionario e um tipo de ausencia
        Quando uma ausencia e criada
        Entao o create do mail.thread recebe mail_auto_subscribe_no_notify=True
        """
        seen, patcher = self._spy("create")
        with patcher:
            leave = self.env["hr.leave"].create(self._leave_vals())
        self.assertTrue(leave)
        flags = self._flags(seen, "hr.leave")
        self.assertTrue(flags, "hr.leave.create deveria chegar no mail.thread")
        self.assertTrue(all(flags))

    def test_leave_write_suppresses_auto_subscribe_notification(self):
        """
        Dado uma ausencia existente
        Quando ela e alterada
        Entao o write do mail.thread recebe mail_auto_subscribe_no_notify=True
        """
        leave = self.env["hr.leave"].create(self._leave_vals())
        seen, patcher = self._spy("write")
        with patcher:
            leave.write({"notes": "Alterada"})
        self.assertEqual(leave.notes, "Alterada")
        flags = self._flags(seen, "hr.leave")
        self.assertTrue(flags)
        self.assertTrue(all(flags))

    def test_allocation_create_suppresses_auto_subscribe_notification(self):
        """
        Dado um funcionario e um tipo de ausencia com alocacao
        Quando uma alocacao e criada
        Entao o create do mail.thread recebe mail_auto_subscribe_no_notify=True
        """
        seen, patcher = self._spy("create")
        with patcher:
            allocation = self.env["hr.leave.allocation"].create(self._allocation_vals())
        self.assertEqual(allocation.number_of_days, 3)
        flags = self._flags(seen, "hr.leave.allocation")
        self.assertTrue(flags)
        self.assertTrue(all(flags))

    def test_allocation_write_suppresses_auto_subscribe_notification(self):
        """
        Dado uma alocacao existente
        Quando ela e alterada
        Entao o write do mail.thread recebe mail_auto_subscribe_no_notify=True
        """
        allocation = self.env["hr.leave.allocation"].create(self._allocation_vals())
        seen, patcher = self._spy("write")
        with patcher:
            allocation.write({"notes": "Alterada"})
        self.assertEqual(allocation.notes, "Alterada")
        flags = self._flags(seen, "hr.leave.allocation")
        self.assertTrue(flags)
        self.assertTrue(all(flags))

    def test_other_models_are_not_affected(self):
        """
        Dado o modulo instalado
        Quando outro modelo com mail.thread e criado (hr.job)
        Entao o flag NAO e injetado (escopo restrito a ausencias e alocacoes)
        """
        seen, patcher = self._spy("create")
        with patcher:
            self.env["hr.job"].create({"name": "Job sem flag"})
        flags = self._flags(seen, "hr.job")
        self.assertTrue(flags)
        self.assertFalse(any(flags))
