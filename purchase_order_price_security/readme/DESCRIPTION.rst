This Odoo module controls unit price editing permission on purchase order lines, allowing only users belonging to a "Can Edit The Price in Purchase" group to modify prices. For other users, the price is displayed as read-only.

The restriction is enforced by the server, not only by the view: a user
outside the group cannot set the unit price of a purchase order line by RPC
or through the ORM (create or write). From such a user a price is accepted
only when it is unchanged or equal to the price computed from the vendor
pricelist or the product cost, so internal flows that send the computed price
keep working. Sections and notes are not restricted. When such a user
duplicates an order, the copied lines are priced again by the system.
