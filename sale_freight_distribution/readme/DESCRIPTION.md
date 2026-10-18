This module distributes the freight cost (amount_freight_value) from a sale order
proportionally across its order lines based on each line's subtotal relative to
the total of storable product lines.

When the sale order is saved or a line is removed, the freight is automatically
recalculated and distributed to each line's freight_value field.
