import re

# Ordered by confidence to keep classification deterministic.
QUOTE_SCENARIO_ORDER = (
    "odoo_quote_marker",
    "gmail_quote_marker",
    "html_blockquote",
    "outlook_reply_divider",
    "outlook_thread_headers",
)

_MARKER_REGEX = {
    "odoo_quote_marker": re.compile(
        r"data-o-mail-quote(?:-node)?\s*=\s*['\"]?1|data-o-mail-quote(?:-node)?",
        re.IGNORECASE,
    ),
    "gmail_quote_marker": re.compile(
        r"gmail_quote|gmail_quote_container|gmail_attr",
        re.IGNORECASE,
    ),
    "html_blockquote": re.compile(r"<blockquote\b", re.IGNORECASE),
}

_OUTLOOK_HEADER_TAG = r"(?:b|strong)"
_OUTLOOK_INNER_TAGS = r"(?:\s*<[^>]+>\s*)*"

_OUTLOOK_FROM_LABEL_RE = re.compile(
    rf"<{_OUTLOOK_HEADER_TAG}[^>]*>{_OUTLOOK_INNER_TAGS}"
    r"(?:from|de)\s*:"
    rf"{_OUTLOOK_INNER_TAGS}</{_OUTLOOK_HEADER_TAG}>",
    re.IGNORECASE | re.DOTALL,
)

_OUTLOOK_SENT_LABEL_RE = re.compile(
    rf"<{_OUTLOOK_HEADER_TAG}[^>]*>{_OUTLOOK_INNER_TAGS}"
    r"(?:sent|enviad[oa](?:\s+em)?)\s*:"
    rf"{_OUTLOOK_INNER_TAGS}</{_OUTLOOK_HEADER_TAG}>",
    re.IGNORECASE | re.DOTALL,
)

_OUTLOOK_TO_LABEL_RE = re.compile(
    rf"<{_OUTLOOK_HEADER_TAG}[^>]*>{_OUTLOOK_INNER_TAGS}"
    r"(?:to|para)\s*:"
    rf"{_OUTLOOK_INNER_TAGS}</{_OUTLOOK_HEADER_TAG}>",
    re.IGNORECASE | re.DOTALL,
)

_OUTLOOK_REPLY_ROOT_RE = re.compile(
    r"id\s*=\s*['\"]divRplyFwdMsg['\"]",
    re.IGNORECASE,
)

_OUTLOOK_DIVIDER_RE = re.compile(
    r"border-top\s*:\s*solid",
    re.IGNORECASE,
)


def _has_outlook_thread_headers(body):
    return (
        bool(_OUTLOOK_FROM_LABEL_RE.search(body))
        and bool(_OUTLOOK_SENT_LABEL_RE.search(body))
        and bool(_OUTLOOK_TO_LABEL_RE.search(body))
    )


def _has_outlook_reply_divider(body):
    if _OUTLOOK_REPLY_ROOT_RE.search(body):
        return True
    # `border-top: solid` alone is too broad; only accept with Outlook-like headers.
    if _OUTLOOK_DIVIDER_RE.search(body) and _has_outlook_thread_headers(body):
        return True
    return False


def collect_quote_signals(html_body):
    body = html_body or ""
    signals = {
        key: bool(pattern.search(body)) for key, pattern in _MARKER_REGEX.items()
    }
    signals["outlook_thread_headers"] = _has_outlook_thread_headers(body)
    signals["outlook_reply_divider"] = _has_outlook_reply_divider(body)
    return signals


def classify_quote_scenario(html_body):
    signals = collect_quote_signals(html_body)
    for scenario in QUOTE_SCENARIO_ORDER:
        if signals.get(scenario):
            return scenario
    return "none"


def should_collapse_history(html_body):
    return classify_quote_scenario(html_body) != "none"
