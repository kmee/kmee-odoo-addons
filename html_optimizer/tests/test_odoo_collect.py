# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import io
import unittest

from odoo.tests import TransactionCase, tagged

from . import test_html_sanitizer, test_quote_boundary, test_quote_detection


@tagged("post_install", "-at_install")
class TestPureSuitesRunUnderOdoo(TransactionCase):
    """Os testes das ferramentas são unittest puro e o runner do Odoo não os
    coleta sozinho: roda as suítes aqui para que o CI as execute de fato."""

    def _run_module(self, module):
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        self.assertGreater(result.testsRun, 0)
        self.assertTrue(result.wasSuccessful(), stream.getvalue())

    def test_html_sanitizer(self):
        self._run_module(test_html_sanitizer)

    def test_quote_boundary(self):
        self._run_module(test_quote_boundary)

    def test_quote_detection(self):
        self._run_module(test_quote_detection)
