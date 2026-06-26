===================================
Helpdesk Mgmt Description Optimizer
===================================

Speeds up ticket forms with heavy ``description`` content (long email chains,
many images, repeated signatures) on ``helpdesk.ticket`` (OCA ``helpdesk_mgmt``)
without ever altering the stored description.

How it works
============

* The ``description`` field stays the full, untouched source of truth, so no
  content is lost on edit, duplicate or reprocessing.
* A derived, stored ``description_summary`` holds an optimized, length-bounded
  preview (responsive/lazy images, zero-width strip, duplicate-block removal,
  empty-paragraph collapse). It is recomputed automatically whenever the
  description changes.
* The form field uses the ``description_optimizer`` widget: in read mode it shows
  the summary with a native "Read More" / "Read Less" toggle that reveals the
  full description; in edit mode it edits the full description normally.

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
