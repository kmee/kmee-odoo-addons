import hashlib
import re
from copy import deepcopy

from lxml import etree
from lxml import html as lxml_html


class HtmlSanitizer:
    MAX_DESCRIPTION_BYTES = 51_200  # 50 KB
    SUMMARY_MAX_CHARS = 1_500
    MAX_CONSECUTIVE_EMPTY_PARAGRAPHS = 2
    MAX_DOM_DEPTH = 15

    def sanitize(self, html: str) -> str:
        """
        Recebe HTML bruto e retorna HTML otimizado.
        Aplica todas as transformações em sequência.
        """
        if not html:
            return html

        result = self.optimize(html)
        return self.create_summary(result)

    def optimize(self, html: str) -> str:
        """Aplica otimizações sem resumir o conteúdo."""
        if not html:
            return html

        result = html
        result = self.remove_zero_width_chars(result)
        result = self.normalize_image_styles(result)
        result = self.add_lazy_load_to_images(result)
        result = self.remove_duplicate_blocks(result)
        result = self.collapse_empty_paragraphs(result)
        return result

    def text_content_length(self, html: str) -> int:
        """Retorna o tamanho do texto visível do HTML."""
        if not html:
            return 0

        try:
            root = lxml_html.fragment_fromstring(html, create_parent="div")
            return len(root.text_content())
        except (etree.ParserError, ValueError):
            text_content = re.sub(r"<[^>]+>", "", html)
            return len(text_content)

    def has_hidden_content(self, html: str) -> bool:
        return self.text_content_length(html) > self.SUMMARY_MAX_CHARS

    def _truncate_node(self, node, remaining_chars):
        if remaining_chars <= 0:
            return None, 0

        new_node = deepcopy(node)
        new_node.clear()
        new_node.attrib.update(node.attrib)

        if node.text:
            new_node.text = node.text[:remaining_chars]
            remaining_chars -= len(new_node.text)

        for child in node:
            if remaining_chars <= 0:
                break

            new_child, remaining_chars = self._truncate_node(child, remaining_chars)
            if new_child is None:
                break

            new_node.append(new_child)

            if child.tail and remaining_chars > 0:
                new_child.tail = child.tail[:remaining_chars]
                remaining_chars -= len(new_child.tail)

        return new_node, remaining_chars

    def _inner_html(self, parent) -> str:
        parts = []
        if parent.text:
            parts.append(parent.text)
        for child in parent:
            parts.append(etree.tostring(child, encoding="unicode", method="html"))
        return "".join(parts)

    def create_summary(self, html: str, max_chars: int | None = None) -> str:
        """Cria um resumo HTML-safe limitado por caracteres visíveis."""
        if not html:
            return html

        max_chars = max_chars or self.SUMMARY_MAX_CHARS
        if self.text_content_length(html) <= max_chars:
            return html

        try:
            root = lxml_html.fragment_fromstring(html, create_parent="div")
        except (etree.ParserError, ValueError):
            return html[:max_chars]

        summary_root = etree.Element("div")
        remaining_chars = max_chars

        if root.text and remaining_chars > 0:
            summary_root.text = root.text[:remaining_chars]
            remaining_chars -= len(summary_root.text)

        for child in root:
            if remaining_chars <= 0:
                break
            new_child, remaining_chars = self._truncate_node(child, remaining_chars)
            if new_child is None:
                break
            summary_root.append(new_child)

        return self._inner_html(summary_root)

    def remove_zero_width_chars(self, html: str) -> str:
        """Remove U+FEFF, U+200B e similares."""
        if not html:
            return html
        # Remove zero-width characters
        result = re.sub(r"[\uFEFF\u200B\u200C\u200D]", "", html)
        return result

    def normalize_image_styles(self, html: str) -> str:
        """
        Remove width/height inline de <img>.
        Substitui por: style="max-width:100%; height:auto;"
        """
        if not html:
            return html

        def replace_img_style(match):
            style_attr = match.group(1)

            # Remove width/height em in, cm (com ou sem decimais)
            new_style = re.sub(
                r"\s*width:\s*[\d.]+\s*(?:in|cm)\s*;?",
                "",
                style_attr,
                flags=re.IGNORECASE,
            )
            new_style = re.sub(
                r"\s*height:\s*[\d.]+\s*(?:in|cm)\s*;?",
                "",
                new_style,
                flags=re.IGNORECASE,
            )

            # Adiciona max-width:100%; height:auto; se não existir
            if "max-width" not in new_style:
                new_style = new_style.strip()
                if new_style and not new_style.endswith(";"):
                    new_style += ";"
                if new_style:
                    new_style += " "
                new_style += "max-width:100%; height:auto;"
                new_style = new_style.strip()

            return f'<img style="{new_style}"'

        # Pattern para capturar <img style="...">
        result = re.sub(
            r'<img\s+style="([^"]*)"', replace_img_style, html, flags=re.IGNORECASE
        )

        # Adiciona style em imgs sem style attribute
        def add_style_to_img(match):
            return '<img style="max-width:100%; height:auto;"' + match.group(0)[5:]

        result = re.sub(
            r"<img(?!\s+style=)", add_style_to_img, result, flags=re.IGNORECASE
        )

        return result

    def add_lazy_load_to_images(self, html: str) -> str:
        """
        Adiciona loading="lazy" em todas as imagens para carregamento assíncrono.
        Preserva loading="eager" se já existir (para imagens above-the-fold).
        """
        if not html:
            return html

        def add_lazy_to_img(match):
            full_match = match.group(0)

            # Se já tem loading attribute, mantém o existente
            if re.search(
                r'\bloading\s*=\s*["\'][^"\']*["\']', full_match, re.IGNORECASE
            ):
                return full_match

            # Adiciona loading="lazy" antes do fechamento da tag
            # Remove o fechamento > ou />
            if full_match.rstrip().endswith("/>"):
                return full_match.rstrip()[:-2] + ' loading="lazy"/>'
            else:
                return full_match.rstrip()[:-1] + ' loading="lazy">'

        # Pattern para capturar tags <img ...>
        result = re.sub(r"<img\s[^>]*>", add_lazy_to_img, html, flags=re.IGNORECASE)

        return result

    def remove_duplicate_blocks(self, html: str) -> str:
        """
        Detecta blocos com conteúdo textual idêntico.
        Mantém apenas a primeira ocorrência. Mínimo 100 chars.
        """
        if not html:
            return html

        # Pattern para capturar tags HTML completas
        tag_pattern = (
            r"<(div|p|span|section|article|header|footer|aside|main|"
            r"blockquote|pre|table|ul|ol|li|dl|dt|dd)(?:\s[^>]*)?>.*?</\1>"
        )

        seen_hashes = set()
        blocks_to_replace = []

        for match in re.finditer(tag_pattern, html, re.DOTALL | re.IGNORECASE):
            block = match.group(0)

            # Extrai apenas o texto para o hash
            text_content = re.sub(r"<[^>]+>", "", block)

            # Verifica se tem pelo menos 100 caracteres
            if len(text_content) >= 100:
                text_hash = hashlib.sha1(text_content.encode("utf-8")).hexdigest()
                if text_hash in seen_hashes:
                    blocks_to_replace.append(block)
                else:
                    seen_hashes.add(text_hash)

        # Remove os blocos duplicados
        result = html
        for block in blocks_to_replace:
            result = result.replace(block, "", 1)

        return result

    def collapse_empty_paragraphs(self, html: str) -> str:
        """
        Reduz sequências de <p>&nbsp;</p> ou <p> </p>.
        Limita a MAX_CONSECUTIVE_EMPTY_PARAGRAPHS consecutivos.
        """
        if not html:
            return html

        # Pattern para detectar parágrafos vazios
        empty_p_pattern = r"<p>\s*(?:&nbsp;|\s)\s*</p>"

        # Encontra todas as sequências de parágrafos vazios
        result = html
        matches = list(re.finditer(empty_p_pattern, result, re.IGNORECASE))

        if not matches:
            return result

        # Processa sequências consecutivas
        i = 0
        while i < len(matches):
            # Conta parágrafos vazios consecutivos
            start = matches[i].start()
            count = 1
            j = i + 1

            while j < len(matches) and matches[j].start() == matches[j - 1].end():
                count += 1
                j += 1

            end = matches[j - 1].end() if j > i else matches[i].end()

            # Se há mais parágrafos vazios que o permitido, reduz
            if count > self.MAX_CONSECUTIVE_EMPTY_PARAGRAPHS:
                empty_p = "<p>&nbsp;</p>"
                replacement = empty_p * self.MAX_CONSECUTIVE_EMPTY_PARAGRAPHS
                result = result[:start] + replacement + result[end:]

                # Recalcula matches após modificação
                matches = list(re.finditer(empty_p_pattern, result, re.IGNORECASE))
                i = 0
            else:
                i = j

        return result

    def truncate(self, html: str) -> tuple:
        """
        Se o HTML superar MAX_DESCRIPTION_BYTES:
          - Retorna (html_truncado, True)
          - html_truncado termina em tag fechada válida
        Caso contrário retorna (html_original, False).
        """
        if not html:
            return (html, False)

        html_bytes = html.encode("utf-8")
        if len(html_bytes) <= self.MAX_DESCRIPTION_BYTES:
            return (html, False)

        # Trunca e busca o último fechamento de tag válido
        truncated = html_bytes[: self.MAX_DESCRIPTION_BYTES].decode(
            "utf-8", errors="ignore"
        )

        # Encontra o último fechamento de tag completo </...>
        last_close_pos = 0
        for match in re.finditer(r"</[a-zA-Z][^>]*>", truncated):
            last_close_pos = match.end()

        if last_close_pos > 0:
            # Corta após o último fechamento de tag
            truncated = truncated[:last_close_pos]

        # Tenta fechar tags abertas usando lxml
        try:
            # Envolva em um elemento root para garantir parsing correto
            wrapped = f"<root>{truncated}</root>"
            doc = lxml_html.fromstring(wrapped)
            # Extrai apenas o conteúdo interno
            truncated = "".join(
                etree.tostring(child, encoding="unicode", method="html")
                for child in doc
            )
        except Exception:  # pylint: disable=broad-except
            # Se não conseguir parsear, mantém o que temos
            pass  # pylint: disable=unnecessary-pass

        return (truncated, True)
