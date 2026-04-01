This module distributes the freight cost of a sale order proportionally
across its order lines based on each line's subtotal value.

Only non-service product lines are considered for freight distribution.
The freight value per unit is calculated as:

    line_freight = (order_freight * line_subtotal / total_subtotal) / line_qty
