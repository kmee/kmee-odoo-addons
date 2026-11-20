This module restricts each accounting journal to a list of user groups, so
that each person of the finance team only sees and posts in some journals:
the billing team in the sales journals, the treasury team in the bank
journals, and so on.

A journal with **Allowed Groups** is visible only to the users of one of
those groups. The restriction also covers what is posted in the journal:
journal entries (invoices and bills included), journal items, payments,
bank statement lines and the invoices analysis. A journal without allowed
groups stays visible to every user, so installing the module changes
nothing until a journal is configured.

The restriction is a global record rule, added on top of the multi-company
rules of Odoo, which stay as they are. It applies to every user, the
accounting administrators included: an exception is made by data, adding
the group of the administrators to the journal. Only the superuser (code
running with sudo) ignores it.
