# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import sys
import unittest
from pathlib import Path

from lxml import html as lxml_html

# Import the pure-Python tools directly, without booting Odoo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from quote_boundary import split_history  # noqa: E402

ALL_FIXTURES = (
    "outlook_divider.html",
    "outlook_mixed_parent.html",
    "outlook_divrplyfwdmsg.html",
    "gmail_quote.html",
    "blockquote.html",
    "odoo_marker.html",
    "odoo_marker_mixed.html",
    "odoo_divrplyfwdmsg_marked.html",
)


def _text_len(html):
    if not html:
        return 0
    return len(lxml_html.fragment_fromstring(html, create_parent="div").text_content())


class TestSplitHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture_dir = Path(__file__).parent / "fixtures" / "html"

    def _read(self, name):
        return (self.fixture_dir / name).read_text(encoding="utf-8")

    def test_every_fixture_splits(self):
        for name in ALL_FIXTURES:
            body = self._read(name)
            result = split_history(body)
            self.assertIsNotNone(result, f"{name}: expected a split, got None")
            main, history = result
            self.assertTrue(history.strip(), f"{name}: history is empty")
            self.assertLess(
                _text_len(main),
                _text_len(body),
                f"{name}: main is not smaller than the original body",
            )

    def test_message_without_history_is_not_split(self):
        body = (
            "<div><p>Ola, segue atualizacao do chamado.</p>"
            "<p>Sem historico citado nesta mensagem.</p></div>"
        )
        self.assertIsNone(split_history(body))

    def test_empty_body_returns_none(self):
        self.assertIsNone(split_history(""))
        self.assertIsNone(split_history(None))

    def test_outlook_mixed_parent_keeps_reply_visible(self):
        # Mixed parent: the most recent reply must stay in `main`.
        main, history = split_history(self._read("outlook_mixed_parent.html"))
        self.assertIn("Boa noite Prezados", main)
        self.assertNotIn("Boa noite Prezados", history)
        self.assertRegex(history, r"border-top\s*:\s*solid")

    def test_gmail_keeps_reply_visible(self):
        main, history = split_history(self._read("gmail_quote.html"))
        self.assertIn("Reply 2, sending to support", main)
        self.assertIn("gmail_quote", history)
        self.assertNotIn("gmail_quote", main)

    def test_odoo_marker_split_keeps_reply_visible(self):
        # Native Odoo marker already present: history goes behind it,
        # the most recent reply stays visible and unmarked.
        main, history = split_history(self._read("odoo_divrplyfwdmsg_marked.html"))
        self.assertIn("Poderiam nos encaminhar", main)
        self.assertIn("data-o-mail-quote", history)
        self.assertNotIn("data-o-mail-quote", main)

    def test_resplitting_main_finds_no_more_history(self):
        # The summarized part must be clean (idempotency of the elision).
        main, _history = split_history(self._read("odoo_divrplyfwdmsg_marked.html"))
        self.assertIsNone(split_history(main))


if __name__ == "__main__":
    unittest.main()
