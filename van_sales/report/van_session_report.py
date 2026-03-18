from odoo import fields, models, tools


class ReportVanSessionLine(models.Model):
    _name = "report.van.session.line"
    _description = "Van Session Line Analysis"
    _auto = False
    _order = "date desc"

    date = fields.Date(readonly=True)
    session_id = fields.Many2one("van.session", readonly=True)
    driver_id = fields.Many2one("res.partner", string="Motorista", readonly=True)
    pos_config_id = fields.Many2one("pos.config", string="POS", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("loaded", "Carregado"),
            ("in_route", "Em Rota"),
            ("returned", "Retornado"),
            ("closed", "Fechado"),
        ],
        readonly=True,
    )
    product_id = fields.Many2one("product.product", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoria", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    qty_out = fields.Float(string="Qtd Saída", readonly=True)
    qty_sold = fields.Float(string="Qtd Vendida", readonly=True)
    qty_returned = fields.Float(string="Qtd Retornada", readonly=True)
    qty_initial = fields.Float(string="Estoque Inicial", readonly=True)
    qty_keep = fields.Float(string="Manter", readonly=True)
    qty_diff = fields.Float(string="Diferença Qtd", readonly=True)
    price_unit = fields.Float(string="Preço Unit.", readonly=True, aggregator="avg")
    amount = fields.Float(string="Valor Diferença", readonly=True)
    amount_sold = fields.Float(string="Valor Vendido", readonly=True)
    amount_loaded = fields.Float(string="Valor Carregado", readonly=True)
    sell_through_rate = fields.Float(string="% Venda", readonly=True, aggregator="avg")
    waived = fields.Boolean(string="Abonado", readonly=True)
    cash_diff = fields.Float(string="Dif. Caixa", readonly=True)
    nbr_lines = fields.Integer(string="# Linhas", readonly=True)

    def _select(self):
        return """
            SELECT
                l.id AS id,
                s.date AS date,
                s.id AS session_id,
                s.driver_id AS driver_id,
                s.pos_config_id AS pos_config_id,
                s.state AS state,
                l.product_id AS product_id,
                pt.categ_id AS categ_id,
                s.company_id AS company_id,
                l.qty_out AS qty_out,
                l.qty_sold AS qty_sold,
                l.qty_returned AS qty_returned,
                l.qty_initial AS qty_initial,
                l.qty_keep AS qty_keep,
                l.qty_diff AS qty_diff,
                l.price_unit AS price_unit,
                l.amount AS amount,
                l.qty_sold * l.price_unit AS amount_sold,
                l.qty_out * l.price_unit AS amount_loaded,
                CASE
                    WHEN l.qty_out = 0 THEN 0
                    ELSE l.qty_sold / l.qty_out * 100
                END AS sell_through_rate,
                l.waived AS waived,
                s.cash_diff AS cash_diff,
                1 AS nbr_lines
        """

    def _from(self):
        return """
            FROM van_session_line l
                JOIN van_session s ON s.id = l.session_id
                JOIN product_product p ON p.id = l.product_id
                JOIN product_template pt ON pt.id = p.product_tmpl_id
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            "CREATE OR REPLACE VIEW %s AS (%s %s)"
            % (self._table, self._select(), self._from())
        )
