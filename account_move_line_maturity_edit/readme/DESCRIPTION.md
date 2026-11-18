Lets selected users edit the due date (date_maturity) of receivable and
payable journal items, including the items of posted entries, from the
Journal Items and Journal Entries lists of the web client.

Posted items can only be changed when they are on a receivable/payable
account, are not reconciled, and are not in a payment order that is not
cancelled. Each change on a posted entry is logged in the chatter of the entry
with the old and the new date.

The Journal Entries action no longer hides the Due Date column
(view_no_maturity is removed from its context).

Scope of the guard: the checks (group, payment order, reconciliation) run only
for edits made through the web client (web_save). This is by design, so that
internal flows that write the due date directly, such as CNAB due-date change
instructions, are not blocked. Writes made through external RPC, imports or
code of other modules are NOT checked. The group is a usability control for
the interface, not an access-control mechanism against API users.
