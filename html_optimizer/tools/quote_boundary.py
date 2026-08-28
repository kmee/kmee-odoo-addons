# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Server-side detection of where quoted email history starts.

Ports the boundary engine that previously lived in JavaScript
(quote_detection_engine.js) to lxml, so the split happens deterministically on
the server instead of fighting the OWL render cycle in the browser.

Public entry point: ``split_history(body_html)`` returns ``(main, history)`` or
``None`` when the body carries no quoted history.
"""

import re

from lxml import etree, html as lxml_html

try:
    from .quote_detection import should_collapse_history
except ImportError:  # pragma: no cover - standalone import for pure unit tests
    from quote_detection import should_collapse_history

_FROM_RE = re.compile(r"^\s*(?:from|de)\s*:", re.IGNORECASE)
_SENT_RE = re.compile(r"^\s*(?:sent|enviad[oa](?:\s+em)?)\s*:", re.IGNORECASE)
_TO_RE = re.compile(r"^\s*(?:to|para)\s*:", re.IGNORECASE)
_BORDER_RE = re.compile(r"border-top\s*:\s*solid", re.IGNORECASE)
_REPLY_ID_RE = re.compile(r"divrplyfwdmsg", re.IGNORECASE)

_QUOTE_CLASSES = frozenset({"gmail_quote", "gmail_quote_container", "gmail_attr"})
_HEADER_TAGS = ("b", "strong")
_CONTENT_TAGS = ("img", "table", "hr", "blockquote")


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _classes(el):
    return set((el.get("class") or "").split())


def _is_selector_boundary(el):
    if el.get("data-o-mail-quote") is not None:
        return True
    if el.get("data-o-mail-quote-node") is not None:
        return True
    if _classes(el) & _QUOTE_CLASSES:
        return True
    if el.tag == "blockquote":
        return True
    el_id = el.get("id") or ""
    if _REPLY_ID_RE.search(el_id):
        return True
    if "signature" in el_id.lower() or "signature" in (el.get("class") or "").lower():
        return True
    return False


def _has_label(el, regex):
    for node in el.iter(*_HEADER_TAGS):
        if regex.match(_norm(node.text_content())):
            return True
    return False


def _looks_like_thread_header(el):
    return (
        _has_label(el, _FROM_RE) and _has_label(el, _SENT_RE) and _has_label(el, _TO_RE)
    )


def _has_meaningful_content(el):
    if _norm(el.text_content()):
        return True
    return any(el.find(".//%s" % tag) is not None for tag in _CONTENT_TAGS)


def _find_by_selectors(root):
    for el in root.iter():
        if el is root:
            continue
        if not isinstance(el.tag, str):
            continue
        if _is_selector_boundary(el):
            return el
    return None


def _build_boundary_from_reply_block(root, reply_block):
    parent = reply_block.getparent()
    if parent is None or parent is root:
        return reply_block
    for sibling in parent:
        if sibling is reply_block:
            break
        if _has_meaningful_content(sibling):
            return reply_block
    return parent


def _find_outlook_anchor(root):
    for bold in root.iter(*_HEADER_TAGS):
        if not _FROM_RE.match(_norm(bold.text_content())):
            continue
        ancestor = bold.getparent()
        while ancestor is not None and ancestor is not root:
            looks_like_reply = _BORDER_RE.search(
                ancestor.get("style") or ""
            ) or _REPLY_ID_RE.search(ancestor.get("id") or "")
            if (
                looks_like_reply
                and _has_label(ancestor, _SENT_RE)
                and _has_label(ancestor, _TO_RE)
            ):
                return _build_boundary_from_reply_block(root, ancestor)
            ancestor = ancestor.getparent()
    return None


def _find_signature_before_reply(root):
    children = [c for c in root if isinstance(c.tag, str)]
    for index, child in enumerate(children):
        identifier = (child.get("id") or "").lower()
        classes = (child.get("class") or "").lower()
        if "signature" not in identifier and "signature" not in classes:
            continue
        for candidate in children[index + 1 : index + 6]:
            candidate_id = candidate.get("id") or ""
            candidate_style = candidate.get("style") or ""
            if (
                _REPLY_ID_RE.search(candidate_id)
                or _BORDER_RE.search(candidate_style)
                or _looks_like_thread_header(candidate)
            ):
                return child
    return None


def find_history_boundary(root):
    """Return the first element that starts the quoted history, or None."""
    candidates = [
        boundary
        for boundary in (
            _find_by_selectors(root),
            _find_outlook_anchor(root),
            _find_signature_before_reply(root),
        )
        if boundary is not None and boundary is not root
    ]
    if not candidates:
        return None
    order = {id(el): position for position, el in enumerate(root.iter())}
    return min(candidates, key=lambda el: order.get(id(el), len(order)))


def _serialize(nodes):
    return "".join(
        etree.tostring(node, encoding="unicode", method="html") for node in nodes
    )


def _serialize_inner(parent):
    parts = [parent.text] if parent.text else []
    parts.extend(
        etree.tostring(child, encoding="unicode", method="html") for child in parent
    )
    return "".join(parts)


def _parse(body_html):
    try:
        return lxml_html.fragment_fromstring(body_html, create_parent="div")
    except (etree.ParserError, etree.LxmlError, ValueError):
        return None


def split_history(body_html):
    """Split a message body into (main, history) at the quote boundary.

    ``main`` is everything before the boundary (the most recent reply) and
    ``history`` is the boundary element plus every following sibling. Returns
    ``None`` when there is no quoted history to collapse.
    """
    if not body_html or not should_collapse_history(body_html):
        return None

    root = _parse(body_html)
    if root is None:
        return None

    boundary = find_history_boundary(root)
    if boundary is None or boundary is root:
        return None

    parent = boundary.getparent()
    if parent is None:
        return None

    history_nodes = []
    node = boundary
    while node is not None:
        history_nodes.append(node)
        node = node.getnext()

    history_html = _serialize(history_nodes)
    for node in history_nodes:
        parent.remove(node)
    main_html = _serialize_inner(root)

    if not history_html.strip():
        return None
    return main_html, history_html
