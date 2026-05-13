This module adds shipping and logistics information to Sales Orders by exposing
operational data already available in stock and delivery flows.

A dedicated **Shipping Information** section is added to the **Other Info** tab of
the Sales Order, allowing users to quickly visualize important logistics metrics
associated with the order:

- **Total Weight** – combined shipping weight of all products in the order
- **Total Volume** – combined shipping volume of all products in the order
- **Longest Dimension** – largest single dimension detected among the order's products

The module reuses existing stock and delivery computations and follows the same
visual structure already used by Odoo in `stock.picking` shipping sections,
including inline units of measure displayed beside metric values.
