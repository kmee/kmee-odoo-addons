==============
HTML Optimizer
==============

Reusable, Odoo-light helpers to make heavy HTML (emails, long descriptions)
render fast while keeping the full content available.

It provides pure-Python tools (no ORM dependency, unit-testable on their own):

* ``tools/html_sanitizer.py`` — strip zero-width characters, make images
  responsive and lazy-loaded, drop duplicated blocks, collapse empty
  paragraphs, and build a visible-character-bounded summary.
* ``tools/quote_detection.py`` — classify which quoted-history scenario a body
  matches (Odoo marker, Gmail, blockquote, Outlook divider/headers).
* ``tools/quote_boundary.py`` — ``split_history(body)`` returns ``(main,
  history)``: the most recent reply and the quoted history that follows it.

This module ships no models or views of its own; it is a base meant to be
reused (for example by ``mail_chatter_quote_summary``).

Credits
=======

Authors
~~~~~~~

* KMEE

License
=======

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
