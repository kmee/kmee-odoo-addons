==========================
Mail Chatter Quote Summary
==========================

Collapses the quoted email history in chatter messages of any model. Each
message first shows only the most recent reply plus a "Ler mais" toggle; the
quoted history is fetched on demand, so long email chains no longer bloat the
chatter payload and DOM.

How it works
============

* The stored ``mail.message.body`` is **never modified**. Only the rendered
  payload (``_message_format``) is summarized, and the full history is streamed
  on demand through the ``load_quote_history_chunk`` RPC, read from the original
  body.
* Detection and the main/history split are deterministic and server-side
  (reused from ``html_optimizer``). The single client-side listener only reacts
  to user clicks; it never mutates the DOM during render.

Configuration
=============

Settings > General Settings > Chatter Quote Summary:

* enable/disable the feature;
* optionally restrict it to specific models (comma-separated technical names);
  empty applies to every chatter.

Only ``email`` and ``comment`` messages are affected.

Credits
=======

Authors
~~~~~~~

* KMEE

License
=======

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
