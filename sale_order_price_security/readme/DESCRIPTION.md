This module creates a group in which only those in this group can edit the sales price in a sale order.

The restriction is enforced by the server, not only by the view: a user
outside the group cannot set the unit price of a sale order line by RPC or
through the ORM (create or write). From such a user a price is accepted only
when it is unchanged or equal to the price computed by the pricelist, so
internal flows that send the computed price keep working. Sections, notes,
down payments, re-invoiced expenses, delivery and reward lines are not
restricted. When such a user duplicates an order, the copied lines are priced
again by the pricelist.
