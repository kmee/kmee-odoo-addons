# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models, tools


class StockValuationLayerCostReport(models.Model):
    _name = "stock.valuation.layer.cost.report"
    _description = "Stock Valuation & Cost"
    _auto = False
    _order = "create_date, id"
    _rec_name = "product_id"

    create_date = fields.Datetime(string="Date", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True, required=True)
    product_id = fields.Many2one(
        "product.product",
        "Product",
        readonly=True,
        required=True,
        check_company=True,
        auto_join=True,
    )
    categ_id = fields.Many2one("product.category", related="product_id.categ_id")
    product_tmpl_id = fields.Many2one(
        "product.template", related="product_id.product_tmpl_id"
    )
    quantity = fields.Float(help="Quantity", digits="Product Unit of Measure")
    uom_id = fields.Many2one(related="product_id.uom_id", readonly=True, required=True)
    currency_id = fields.Many2one(
        "res.currency",
        "Currency",
        related="company_id.currency_id",
        readonly=True,
        required=True,
    )
    unit_cost = fields.Monetary(
        readonly=True,
        default=0.0,
        aggregator="avg",
        help="Unit Cost is calculated as a moving average.",
    )
    value = fields.Monetary("Total Value")
    remaining_qty = fields.Float(digits="Product Unit of Measure")
    stock_qty = fields.Float(
        digits="Stock Total Quantity",
        readonly=True,
        default=0.0,
    )
    stock_value = fields.Float(
        digits="Stock Total Value",
        readonly=True,
        default=0.0,
    )
    remaining_value = fields.Monetary(readonly=True)
    description = fields.Char(readonly=True)
    stock_move_id = fields.Many2one(
        "stock.move", "Stock Move", check_company=True, index=True
    )
    account_move_id = fields.Many2one(
        "account.move", "Journal Entry", check_company=True, index=True
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW stock_valuation_layer_cost_report AS
            WITH base AS (
                SELECT
                    svl.id AS id,
                    svl.create_date AS create_date,
                    svl.company_id AS company_id,
                    svl.product_id AS product_id,
                    svl.quantity AS quantity,
                    svl.remaining_qty AS remaining_qty,
                    svl.remaining_value AS remaining_value,
                    svl.value AS value,
                    svl.description AS description,
                    svl.stock_move_id AS stock_move_id,
                    svl.account_move_id AS account_move_id,

                    SUM(svl.value) OVER w AS cumulative_value,
                    SUM(svl.quantity) OVER w AS cumulative_qty
                FROM stock_valuation_layer svl
                WINDOW w AS (
                    PARTITION BY svl.company_id, svl.product_id
                    ORDER BY svl.id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
            )
            SELECT
                id,
                create_date,
                company_id,
                product_id,
                quantity,
                remaining_qty,
                remaining_value,
                value,
                description,
                stock_move_id,
                account_move_id,

                cumulative_value AS cumulative_value,
                cumulative_qty AS cumulative_qty,

                -- fields mirroring cumulative values
                cumulative_qty AS stock_qty,
                cumulative_value AS stock_value,

                CASE
                    WHEN cumulative_qty = 0
                        THEN LAG(
                                CASE WHEN cumulative_qty = 0
                                    THEN NULL
                                    ELSE cumulative_value / NULLIF(cumulative_qty, 0)
                                END
                            ) OVER (PARTITION BY company_id, product_id ORDER BY id)
                    ELSE cumulative_value / NULLIF(cumulative_qty, 0)
                END AS unit_cost
            FROM base
            """
        )
