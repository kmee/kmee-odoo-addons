# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeadlineTrack(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Chatter owner"})
        cls.todo = cls.env.ref("mail.mail_activity_data_todo")
        cls.today = date(2026, 1, 10)

    def _activity(self, summary="Call customer", **kw):
        vals = {
            "res_model_id": self.env["ir.model"]._get_id("res.partner"),
            "res_id": self.partner.id,
            "activity_type_id": self.todo.id,
            "summary": summary,
            "date_deadline": self.today,
            "user_id": self.env.user.id,
        }
        vals.update(kw)
        return self.env["mail.activity"].create(vals)

    def _deadline_messages(self):
        return self.partner.message_ids.filtered(
            lambda m: "Deadline alterado" in (m.body or "")
        )

    def test_changing_deadline_posts_message_on_record(self):
        """Given an activity linked to a partner
        When its deadline is moved to another date
        Then a chatter message with summary, old and new date is posted."""
        activity = self._activity()
        new = self.today + timedelta(days=3)
        activity.write({"date_deadline": new})
        messages = self._deadline_messages()
        self.assertEqual(len(messages), 1)
        for text in ("Call customer", str(self.today), str(new)):
            self.assertIn(text, messages.body)
        self.assertEqual(activity.date_deadline, new)

    def test_same_deadline_does_not_post(self):
        """Given an activity
        When the deadline is written with the same value (date or string)
        Then no message is posted."""
        activity = self._activity()
        activity.write({"date_deadline": self.today})
        activity.write({"date_deadline": str(self.today)})
        self.assertFalse(self._deadline_messages())

    def test_other_fields_do_not_post(self):
        """Given an activity
        When a field other than the deadline changes
        Then nothing is posted."""
        activity = self._activity()
        activity.write({"summary": "New summary"})
        self.assertFalse(self._deadline_messages())

    def test_message_falls_back_to_activity_type_name(self):
        """Given an activity without summary
        When the deadline changes
        Then the message names the activity type instead."""
        activity = self._activity(summary=False)
        activity.write({"date_deadline": self.today + timedelta(days=1)})
        self.assertIn(self.todo.name, self._deadline_messages().body)

    def test_each_activity_posts_its_own_message(self):
        """Given two activities on the same record
        When both deadlines are changed in one write
        Then one message per activity is posted."""
        acts = self._activity("A") | self._activity("B")
        acts.write({"date_deadline": self.today + timedelta(days=7)})
        messages = self._deadline_messages()
        self.assertEqual(len(messages), 2)
        self.assertIn("A", messages[0].body + messages[1].body)
        self.assertIn("B", messages[0].body + messages[1].body)
