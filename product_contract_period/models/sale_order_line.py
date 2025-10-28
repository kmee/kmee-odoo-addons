# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Adicionando campos de período na linha de pedido para contratos
    period_qty = fields.Float(
        string="Quantidade de Licenças",
        default=1.0,
        help="Quantidade de licenças fornecidas em cada período",
    )
    period_count = fields.Integer(
        string="Número de Meses", default=1, help="Número total de meses para o contrato"
    )
    period_amount = fields.Monetary(
        string="Valor Mensal",
        compute="_compute_period_amount",
        store=True,
        help="Valor por período = Qtd * (Valor Unitário - Desconto)",
    )

    # Sobrescrever para transferir valores ao criar linhas de contrato
    def _prepare_contract_line_values(
        self, contract, predecessor_contract_line_id=False
    ):
        values = super(SaleOrderLine, self)._prepare_contract_line_values(
            contract, predecessor_contract_line_id
        )
        values.update(
            {
                "period_qty": self.period_qty,
                "period_count": self.period_count,
                "quantity": self.period_qty,  # Quantidade por período
            }
        )
        return values

    # Atualizar o método de cálculo da data de término
    def _get_date_end(self):
        self.ensure_one()
        date_end = self.date_start
        rule_type = self._get_auto_renew_rule_type()

        if rule_type == "daily":
            date_end += relativedelta(days=(self.period_count)) - relativedelta(days=1)
        elif rule_type == "weekly":
            date_end += relativedelta(weeks=(self.period_count)) - relativedelta(days=1)
        elif rule_type == "monthly":
            date_end += relativedelta(months=(self.period_count)) - relativedelta(
                days=1
            )
        elif rule_type == "yearly":
            date_end += relativedelta(years=(self.period_count)) - relativedelta(days=1)

        return date_end

    @api.depends("period_qty", "price_unit", "discount", "period_count")
    def _compute_period_amount(self):
        for line in self:
            # Calcula o preço com desconto
            price_with_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            # Calcula valor por período
            line.period_amount = line.period_qty * price_with_discount

    @api.onchange("period_qty", "period_count", "price_unit", "discount")
    def _onchange_period(self):
        for record in self:
            if record.product_id.is_contract:
                # A quantidade total é usada apenas para cálculos na ordem de venda
                record.product_uom_qty = record.period_qty * record.period_count
                # Recalcular a data de fim com base na nova configuração de períodos
                record.date_end = record._get_date_end()

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.period_qty = self.product_id.default_period_qty
            self.period_count = self.product_id.default_period_count
