# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import signal
import unittest
from pathlib import Path

try:
    from odoo.addons.html_optimizer.tools.quote_detection import (
        classify_quote_scenario,
        collect_quote_signals,
        should_collapse_history,
    )
except ModuleNotFoundError:
    import importlib.util

    _module_path = Path(__file__).resolve().parents[1] / "tools" / "quote_detection.py"
    _spec = importlib.util.spec_from_file_location(
        "html_optimizer.tools.quote_detection",
        _module_path,
    )
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    classify_quote_scenario = _module.classify_quote_scenario
    collect_quote_signals = _module.collect_quote_signals
    should_collapse_history = _module.should_collapse_history

# Synthetic fixtures (no personal data) reproducing each real-world structure.
FIXTURE_SCENARIOS = {
    "outlook_divider.html": "outlook_reply_divider",
    "outlook_mixed_parent.html": "outlook_reply_divider",
    "outlook_divrplyfwdmsg.html": "outlook_reply_divider",
    "gmail_quote.html": "gmail_quote_marker",
    "blockquote.html": "html_blockquote",
    "odoo_marker.html": "odoo_quote_marker",
    "odoo_marker_mixed.html": "odoo_quote_marker",
    "odoo_divrplyfwdmsg_marked.html": "odoo_quote_marker",
}


class TestQuoteDetection(unittest.TestCase):
    """Regression suite for all known quote-history scenarios."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture_dir = Path(__file__).parent / "fixtures" / "html"

    def _read_fixture(self, name):
        return (self.fixture_dir / name).read_text(encoding="utf-8")

    def test_all_fixtures_are_collapsible(self):
        for name in FIXTURE_SCENARIOS:
            self.assertTrue(
                should_collapse_history(self._read_fixture(name)),
                f"{name} should be detected as quoted history",
            )

    def test_fixtures_have_expected_primary_scenario(self):
        for name, expected in FIXTURE_SCENARIOS.items():
            got = classify_quote_scenario(self._read_fixture(name))
            self.assertEqual(got, expected, f"{name}: expected {expected}, got {got}")

    def test_odoo_marker_signal_detected(self):
        html = self._read_fixture("odoo_divrplyfwdmsg_marked.html")
        self.assertTrue(collect_quote_signals(html)["odoo_quote_marker"])

    def test_non_quoted_message_does_not_collapse(self):
        html = """
            <div>
                <p>Ola, segue atualizacao do chamado.</p>
                <p>Sem historico citado nesta mensagem.</p>
            </div>
        """
        self.assertFalse(should_collapse_history(html))
        self.assertEqual(classify_quote_scenario(html), "none")

    def test_outlook_divider_without_full_headers_does_not_collapse(self):
        html = """
            <div>
                <p>Atualizacao principal para o cliente.</p>
                <div style="border-top: solid #e1e1e1 1pt; padding-top: 4px;">
                    <b>De:</b> Atendimento XPTO<br/>
                    <b>Enviado:</b> sexta-feira, 1 de maio de 2026 11:05
                </div>
            </div>
        """
        signals = collect_quote_signals(html)
        self.assertFalse(signals["outlook_thread_headers"])
        self.assertFalse(signals["outlook_reply_divider"])
        self.assertFalse(should_collapse_history(html))

    def test_outlook_divider_with_full_headers_collapses(self):
        html = """
            <div>
                <p>Mensagem principal mais recente.</p>
                <div style="border-top: solid #e1e1e1 1pt; padding-top: 4px;">
                    <b>De:</b> Cliente Exemplo<br/>
                    <b>Enviado:</b> sexta-feira, 1 de maio de 2026 11:05<br/>
                    <b>Para:</b> suporte@example.com
                </div>
                <div>Texto de historico antigo.</div>
            </div>
        """
        signals = collect_quote_signals(html)
        self.assertTrue(signals["outlook_thread_headers"])
        self.assertTrue(signals["outlook_reply_divider"])
        self.assertEqual(classify_quote_scenario(html), "outlook_reply_divider")

    def test_outlook_headers_with_nested_tags_collapses(self):
        html = """
            <div>
                <p>Mensagem principal.</p>
                <div style="border:none; border-top:solid #E1E1E1 1.0pt; padding:3.0pt 0cm 0cm 0cm">
                    <p>
                        <b><span>De:</span></b><span> Remetente</span><br/>
                        <b><span>Enviada em:</span></b><span> segunda-feira, 13 de abril de 2026 11:45</span><br/>
                        <b><span>Para:</span></b><span> destinatario@example.com</span>
                    </p>
                </div>
            </div>
        """
        signals = collect_quote_signals(html)
        self.assertTrue(signals["outlook_thread_headers"])
        self.assertTrue(signals["outlook_reply_divider"])
        self.assertEqual(classify_quote_scenario(html), "outlook_reply_divider")

    @unittest.skipUnless(
        hasattr(signal, "SIGALRM"), "SIGALRM-based time guard is Unix only"
    )
    def test_bold_run_without_header_stays_linear(self):
        poison = "<div><b> " + "<span></span> " * 60 + "no header label</b></div>"

        def _timeout(signum, frame):
            raise AssertionError("quote detection took too long (regex backtracking)")

        previous = signal.signal(signal.SIGALRM, _timeout)
        signal.setitimer(signal.ITIMER_REAL, 5)
        try:
            self.assertFalse(should_collapse_history(poison))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    unittest.main()
