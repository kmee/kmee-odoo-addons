import sys
import unittest

# Importe direto para evitar carregar o modelo Odoo
SYS_PATH_INSERT = "/opt/odoo/custom/src/private/helpdesk_description_optimizer/models"
sys.path.insert(0, SYS_PATH_INSERT)
from html_sanitizer import HtmlSanitizer  # noqa: E402


class TestRemoveZeroWidthChars(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def test_removes_feff(self):
        """U+FEFF (BOM / zero-width no-break space) deve ser removido"""
        result = self.s.remove_zero_width_chars("Olá\ufeffmundo")
        self.assertNotIn("\ufeff", result)
        self.assertEqual(result, "Olámundo")

    def test_removes_zero_width_space(self):
        """U+200B (zero-width space) deve ser removido"""
        result = self.s.remove_zero_width_chars("abc\u200bdef")
        self.assertNotIn("\u200b", result)

    def test_removes_zero_width_joiner(self):
        """U+200D deve ser removido"""
        result = self.s.remove_zero_width_chars("abc\u200ddef")
        self.assertNotIn("\u200d", result)

    def test_preserves_normal_content(self):
        """Conteúdo sem caracteres especiais não deve ser alterado"""
        html = "<p>Texto normal com acentos: ção</p>"
        self.assertEqual(self.s.remove_zero_width_chars(html), html)

    def test_empty_string(self):
        self.assertEqual(self.s.remove_zero_width_chars(""), "")


class TestNormalizeImageStyles(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def test_removes_width_in_inches(self):
        html = '<img style="width:14.375in; height:4.1875in" src="/img">'
        result = self.s.normalize_image_styles(html)
        self.assertNotIn("14.375in", result)
        self.assertNotIn("4.1875in", result)
        self.assertIn("max-width:100%", result)
        self.assertIn("height:auto", result)

    def test_removes_width_in_cm(self):
        html = '<img style="width:36.5cm; height:10cm" src="/img">'
        result = self.s.normalize_image_styles(html)
        self.assertNotIn("36.5cm", result)
        self.assertIn("max-width:100%", result)

    def test_integer_inches_removed(self):
        html = '<img style="width:10in; height:2in" src="/img">'
        result = self.s.normalize_image_styles(html)
        self.assertNotIn("10in", result)

    def test_img_without_style_unchanged(self):
        html = '<img src="/logo.png" alt="logo">'
        result = self.s.normalize_image_styles(html)
        self.assertIn('src="/logo.png"', result)
        self.assertIn("max-width:100%", result)

    def test_non_img_tags_untouched(self):
        html = '<div style="width:500px"><p>texto</p></div>'
        result = self.s.normalize_image_styles(html)
        self.assertIn("width:500px", result)

    def test_multiple_images(self):
        html = '<img style="width:10in" src="/a"><img style="width:5in" src="/b">'
        result = self.s.normalize_image_styles(html)
        self.assertEqual(result.count("max-width:100%"), 2)
        self.assertNotIn("10in", result)
        self.assertNotIn("5in", result)


class TestRemoveDuplicateBlocks(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def _disclaimer(self, n=1):
        """Gera um bloco de disclaimer longo (>100 chars) repetido n vezes."""
        block = (
            "<div>***********************<br>"
            "Caso tenha recebido indevidamente, por favor delete este e-mail. "
            "In case you received this improperly please delete immediately. "
            "***********************</div>"
        )
        return block * n

    def test_single_block_kept(self):
        html = self._disclaimer(1)
        result = self.s.remove_duplicate_blocks(html)
        self.assertEqual(result.count("Caso tenha recebido"), 1)

    def test_duplicate_removed(self):
        html = self._disclaimer(3)
        result = self.s.remove_duplicate_blocks(html)
        self.assertEqual(result.count("Caso tenha recebido"), 1)

    def test_ten_duplicates_become_one(self):
        html = self._disclaimer(10)
        result = self.s.remove_duplicate_blocks(html)
        self.assertEqual(result.count("Caso tenha recebido"), 1)

    def test_short_blocks_not_deduplicated(self):
        """Blocos com menos de 100 chars de texto não são deduplicados."""
        html = "<p>ok</p><p>ok</p><p>ok</p>"
        result = self.s.remove_duplicate_blocks(html)
        self.assertEqual(result.count("<p>ok</p>"), 3)

    def test_different_blocks_preserved(self):
        html = (
            "<div>Bloco A com conteúdo suficientemente longo para ser considerado "
            * 3
            + "</div>"
            "<div>Bloco B com conteúdo diferente suficientemente longo aqui  "
            * 3
            + "</div>"
        )
        result = self.s.remove_duplicate_blocks(html)
        self.assertIn("Bloco A", result)
        self.assertIn("Bloco B", result)


class TestCollapseEmptyParagraphs(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def test_three_empty_become_two(self):
        html = "<p>Texto</p>" + "<p>&nbsp;</p>" * 3 + "<p>Fim</p>"
        result = self.s.collapse_empty_paragraphs(html)
        self.assertLessEqual(
            result.count("<p>&nbsp;</p>"),
            HtmlSanitizer.MAX_CONSECUTIVE_EMPTY_PARAGRAPHS,
        )

    def test_ten_empty_become_two(self):
        html = "<p>&nbsp;</p>" * 10
        result = self.s.collapse_empty_paragraphs(html)
        self.assertLessEqual(result.count("<p>&nbsp;</p>"), 2)

    def test_two_empty_unchanged(self):
        html = "<p>A</p><p>&nbsp;</p><p>&nbsp;</p><p>B</p>"
        result = self.s.collapse_empty_paragraphs(html)
        self.assertEqual(result.count("<p>&nbsp;</p>"), 2)

    def test_empty_p_with_space_also_collapsed(self):
        html = "<p> </p>" * 5
        result = self.s.collapse_empty_paragraphs(html)
        empty_count = result.count("<p> </p>") + result.count("<p>&nbsp;</p>")
        self.assertLessEqual(empty_count, 2)

    def test_non_empty_paragraphs_preserved(self):
        html = "<p>A</p><p>B</p><p>C</p>"
        result = self.s.collapse_empty_paragraphs(html)
        self.assertIn("<p>A</p>", result)
        self.assertIn("<p>B</p>", result)
        self.assertIn("<p>C</p>", result)


class TestTruncate(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def _html_of_size(self, target_kb: int) -> str:
        """Gera HTML com aproximadamente target_kb KB."""
        chunk = "<p>" + "a" * 100 + "</p>\n"
        repeat = (target_kb * 1024) // len(chunk.encode()) + 1
        return chunk * repeat

    def test_small_html_not_truncated(self):
        html = "<p>Texto pequeno</p>"
        result, was_truncated = self.s.truncate(html)
        self.assertFalse(was_truncated)
        self.assertEqual(result, html)

    def test_large_html_is_truncated(self):
        html = self._html_of_size(100)  # 100KB > 50KB limit
        result, was_truncated = self.s.truncate(html)
        self.assertTrue(was_truncated)
        self.assertLessEqual(
            len(result.encode()), HtmlSanitizer.MAX_DESCRIPTION_BYTES + 500
        )

    def test_truncated_html_ends_with_closed_tag(self):
        html = self._html_of_size(100)
        result, _ = self.s.truncate(html)
        # Não deve terminar com tag aberta ou texto truncado
        self.assertFalse(result.rstrip().endswith("<p>"))
        self.assertTrue(result.rstrip().endswith(">"))

    def test_truncated_html_is_parseable(self):
        from lxml import etree

        html = self._html_of_size(100)
        result, _ = self.s.truncate(html)
        # lxml deve conseguir parsear sem erros fatais
        try:
            etree.fromstring(f"<root>{result}</root>")
            parseable = True
        except etree.XMLSyntaxError:
            parseable = False
        self.assertTrue(parseable)

    def test_exactly_at_limit_not_truncated(self):
        html = "a" * HtmlSanitizer.MAX_DESCRIPTION_BYTES
        result, was_truncated = self.s.truncate(html)
        self.assertFalse(was_truncated)


class TestSanitizePipeline(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.s = HtmlSanitizer()

    def test_sanitize_applies_all_transformations(self):
        """O método sanitize() deve encadear todas as transformações."""
        disclaimer = (
            "<div>**** Caso tenha recebido indevidamente delete este e-mail. "
            "In case you received this improperly please delete. ****</div>"
        )
        html = (
            "\ufeff<p>Conteúdo real</p>"
            + "<p>&nbsp;</p>" * 5
            + '<img style="width:15in" src="/img">'
            + disclaimer * 4
        )
        result = self.s.sanitize(html)

        self.assertNotIn("\ufeff", result)
        self.assertLessEqual(result.count("<p>&nbsp;</p>"), 2)
        self.assertNotIn("15in", result)
        self.assertIn("max-width:100%", result)
        self.assertEqual(result.count("Caso tenha recebido"), 1)

    def test_sanitize_is_idempotent(self):
        """Rodar sanitize() duas vezes deve produzir o mesmo resultado."""
        html = (
            "<p>\ufeffTexto</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>"
            '<img style="width:10in" src="/x">'
        )
        first = self.s.sanitize(html)
        second = self.s.sanitize(first)
        self.assertEqual(first, second)

    def test_sanitize_preserves_real_content(self):
        """Conteúdo legítimo não deve ser removido."""
        html = "<p>Prezados, bom dia.</p><p>Segue o relatório solicitado.</p>"
        result = self.s.sanitize(html)
        self.assertIn("Prezados, bom dia.", result)
        self.assertIn("Segue o relatório solicitado.", result)

    def test_sanitize_limits_summary_to_1500_visible_chars(self):
        html = "<p>" + ("a" * 1600) + "</p>"
        result = self.s.sanitize(html)
        self.assertLessEqual(
            self.s.text_content_length(result), HtmlSanitizer.SUMMARY_MAX_CHARS
        )

    def test_short_content_does_not_get_collapsed(self):
        html = "<p>" + ("a" * 100) + "</p>"
        optimized = self.s.optimize(html)
        self.assertFalse(self.s.has_hidden_content(optimized))
        self.assertEqual(self.s.create_summary(optimized), optimized)

    def test_email_with_signature_and_image_lazy_load(self):
        """
        Teste com e-mail realista contendo assinatura e imagem.
        A imagem deve ter lazy loading (loading="lazy") e estilo responsivo.
        """
        html = """
        <div class="note-editable odoo-editor-editable" id="description">
            <p><span style="font-size:12.0pt; font-family:&quot;Aptos&quot;,sans-serif">
                Bom dia <a href="mailto:anne.fake@agcapital.com.br">@Anne Fake</a>, tudo bem?
            </span></p>
            <p><span style="font-size:12.0pt; font-family:&quot;Aptos&quot;,sans-serif">&nbsp;</span></p>
            <p><span style="font-size:12.0pt; font-family:&quot;Aptos&quot;,sans-serif">
                Precisamos fazer o levantamento dos valores e créditos apurados nos últimos anos.
            </span></p>
            <p><span style="font-size:12.0pt; font-family:&quot;Aptos&quot;,sans-serif">&nbsp;</span></p>
            <p><span style="font-size:12.0pt; font-family:&quot;Aptos&quot;,sans-serif">Att,</span></p>
            <div>
                <p><b><span style="font-size:8.0pt">DENISE FAKE</span></b></p>
                <p><span style="font-size:8.0pt">Finance - tax</span></p>
            </div>
            <p>&nbsp;</p>
            <div>
                <p><b>De:</b> Anne Fake &lt;anne.fake@agcapital.com.br&gt;</p>
                <p><b>Enviada em:</b> terça-feira, 18 de março de 2025 14:40</p>
                <p><b>Assunto:</b> [External] RES: Ciência do processo</p>
            </div>
            <p>&nbsp;</p>
            <p>Prezada Denise, boa tarde.</p>
            <p>Adiciono o setor responsável pelo relatório.</p>
            <p>+ @Contencioso</p>
            <div>
                <p>Atenciosamente,</p>
                <p>
                    <img src="/web/image/180715?access_token=fake-token-123"
                         id="Imagem_x0020_93098989"
                         style="width:6.1458in; height:3.618in"
                         height="347"
                         width="590"
                         border="0">
                </p>
            </div>
        </div>
        """

        result = self.s.sanitize(html)

        # Verifica que a imagem tem lazy loading
        self.assertIn(
            'loading="lazy"',
            result,
            'Imagem deve ter atributo loading="lazy" para carregamento assíncrono',
        )

        # Verifica que dimensões em polegadas foram removidas
        self.assertNotIn("6.1458in", result, "Largura em polegadas deve ser removida")
        self.assertNotIn("3.618in", result, "Altura em polegadas deve ser removida")

        # Verifica que tem estilo responsivo
        self.assertIn(
            "max-width:100%", result, "Imagem deve ter estilo responsivo max-width:100%"
        )
        self.assertIn(
            "height:auto", result, "Imagem deve ter height:auto para responsividade"
        )

        # Verifica que conteúdo real foi preservado
        self.assertIn("Bom dia", result)
        self.assertIn("Anne Fake", result)
        self.assertIn("Precisamos fazer o levantamento", result)
        self.assertIn("DENISE FAKE", result)
        self.assertIn("Finance - tax", result)

        # Verifica que zero-width chars foram removidos (se houver)
        self.assertNotIn("\ufeff", result)

        # Verifica que parágrafos vazios foram colapsados
        self.assertLessEqual(result.count("<p>&nbsp;</p>"), 2)

    def test_lazy_load_multiple_images(self):
        """Múltiplas imagens devem ter lazy loading."""
        html = """
        <div>
            <img src="/img1.png" style="width:10in; height:5in">
            <img src="/img2.png" style="width:8in; height:4in">
            <img src="/img3.png" style="width:6in; height:3in">
        </div>
        """
        result = self.s.sanitize(html)

        # Todas as imagens devem ter lazy loading
        self.assertEqual(
            result.count('loading="lazy"'),
            3,
            'Todas as imagens devem ter loading="lazy"',
        )

        # Todas devem ter estilo responsivo
        self.assertEqual(result.count("max-width:100%"), 3)
        self.assertEqual(result.count("height:auto"), 3)

        # Nenhuma dimensão em polegadas deve permanecer
        self.assertNotIn("10in", result)
        self.assertNotIn("8in", result)
        self.assertNotIn("6in", result)

    def test_lazy_load_already_has_loading_attribute(self):
        """Imagem que já tem loading attribute deve ser preservada."""
        html = '<img src="/img.png" style="width:5in" loading="eager">'
        result = self.s.sanitize(html)

        # Deve manter o loading="eager" se já existir
        self.assertIn('loading="eager"', result)
        self.assertNotIn("5in", result)
        self.assertIn("max-width:100%", result)
