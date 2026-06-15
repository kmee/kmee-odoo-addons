=================================
Helpdesk Mgmt Description Optimizer
=================================

Applies the generic ``html_optimizer`` mixin to the ``description`` field of
``helpdesk.ticket`` (OCA ``helpdesk_mgmt``). Heavy descriptions (long emails,
many images, repeated signatures) are stored summarized in ``description`` while
the full optimized content is kept in ``description_full`` and loaded on demand,
so ticket forms open faster.

Features
========

* On create/write the description is sanitized (responsive/lazy images,
  zero-width strip, duplicate-block removal, empty-paragraph collapse) and
  summarized; the full content is preserved in ``description_full``.
* A "Ler mais" toggle on the form lazily fetches the full content in chunks.
* A server action and a disabled one-off cron ("Reprocess helpdesk
  descriptions") reprocess legacy tickets through ``queue_job``.

This is the community counterpart of the AG enterprise description optimizer; it
targets ``helpdesk_mgmt`` (not the enterprise ``helpdesk`` module).

Credits
=======

Authors
~~~~~~~

* KMEE

License
=======

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
