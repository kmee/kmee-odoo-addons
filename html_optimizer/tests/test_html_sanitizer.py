# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import sys
import unittest
from pathlib import Path

# Import the pure-Python tool directly, without booting Odoo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from html_sanitizer import HtmlSanitizer  # noqa: E402

ZWSP = chr(0x200B)
BOM = chr(0xFEFF)


class TestHtmlSanitizer(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def test_removes_zero_width_chars(self):
        result = self.s.remove_zero_width_chars(f"Ola{BOM}mundo{ZWSP}!")
        self.assertNotIn(BOM, result)
        self.assertNotIn(ZWSP, result)
        self.assertEqual(result, "Olamundo!")

    def test_preserves_normal_content(self):
        html = "<p>Texto normal com acentos: cao</p>"
        self.assertEqual(self.s.remove_zero_width_chars(html), html)

    def test_normalize_image_styles_removes_inches(self):
        result = self.s.normalize_image_styles(
            '<img style="width:14.375in; height:4.1875in" src="/img">'
        )
        self.assertNotIn("14.375in", result)
        self.assertIn("max-width:100%", result)
        self.assertIn("height:auto", result)

    def test_normalize_image_styles_adds_style_when_missing(self):
        result = self.s.normalize_image_styles('<img src="/logo.png">')
        self.assertIn("max-width:100%", result)

    def test_non_img_tags_untouched_by_normalize(self):
        html = '<div style="width:500px"><p>texto</p></div>'
        self.assertIn("width:500px", self.s.normalize_image_styles(html))

    def test_add_lazy_load(self):
        result = self.s.add_lazy_load_to_images('<img src="/a.png">')
        self.assertIn('loading="lazy"', result)

    def test_keeps_existing_loading_attribute(self):
        result = self.s.add_lazy_load_to_images('<img src="/a.png" loading="eager">')
        self.assertIn('loading="eager"', result)
        self.assertNotIn('loading="lazy"', result)

    def test_remove_duplicate_blocks(self):
        block = (
            "<div>Bloco com conteudo suficientemente longo para passar dos cem "
            "caracteres exigidos pela deduplicacao do sanitizer.</div>"
        )
        result = self.s.remove_duplicate_blocks(block * 3)
        self.assertEqual(result.count("Bloco com conteudo"), 1)

    def test_short_blocks_not_deduplicated(self):
        result = self.s.remove_duplicate_blocks("<p>ok</p><p>ok</p><p>ok</p>")
        self.assertEqual(result.count("<p>ok</p>"), 3)

    def test_collapse_empty_paragraphs(self):
        html = "<p>A</p>" + "<p>&nbsp;</p>" * 5 + "<p>B</p>"
        result = self.s.collapse_empty_paragraphs(html)
        self.assertLessEqual(
            result.count("<p>&nbsp;</p>"),
            HtmlSanitizer.MAX_CONSECUTIVE_EMPTY_PARAGRAPHS,
        )

    def test_create_summary_limits_visible_chars(self):
        html = "<p>" + ("a" * 1600) + "</p>"
        result = self.s.create_summary(html)
        self.assertLessEqual(
            self.s.text_content_length(result), HtmlSanitizer.SUMMARY_MAX_CHARS
        )

    def test_short_content_not_summarized(self):
        html = "<p>" + ("a" * 100) + "</p>"
        self.assertFalse(self.s.has_hidden_content(html))
        self.assertEqual(self.s.create_summary(html), html)

    def test_truncate_small_html_untouched(self):
        html = "<p>Texto pequeno</p>"
        result, truncated = self.s.truncate(html)
        self.assertFalse(truncated)
        self.assertEqual(result, html)

    def test_truncate_large_html_closes_tags(self):
        html = ("<p>" + "a" * 100 + "</p>\n") * 1000
        result, truncated = self.s.truncate(html)
        self.assertTrue(truncated)
        self.assertTrue(result.rstrip().endswith(">"))

    def test_sanitize_pipeline_is_idempotent(self):
        html = (
            f"<p>{BOM}Texto</p>"
            + "<p>&nbsp;</p>" * 5
            + '<img style="width:10in" src="/x">'
        )
        first = self.s.sanitize(html)
        self.assertEqual(first, self.s.sanitize(first))

    def test_sanitize_preserves_real_content(self):
        html = "<p>Prezados, bom dia.</p><p>Segue o relatorio solicitado.</p>"
        result = self.s.sanitize(html)
        self.assertIn("Prezados, bom dia.", result)
        self.assertIn("Segue o relatorio solicitado.", result)


if __name__ == "__main__":
    unittest.main()
