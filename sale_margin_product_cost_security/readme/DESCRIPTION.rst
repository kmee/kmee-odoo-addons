This module extends the functionality of the product_cost_security module to
the cost and margin fields of the sale_margin module.

When the user does not belong to the group product_cost_group, the server
refuses to read or write the cost (``purchase_price``) and the margin
(``margin``, ``margin_percent``) of sale order lines, the margin of sale
orders and the margin of the sales report, by RPC or through the ORM,
including grouped reads. The fields are also removed from the views.
