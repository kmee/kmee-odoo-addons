from odoo import fields, models


class BenefitType(models.Model):
    _name = "hr.benefit.type"

    contract_id = fields.Many2one(
        string="Contract",
        comodel_name="hr.contract",
        ondelete="restrict",
    )

    benefit_type_id = fields.Many2one(
        string="Tipo do benefício",
        comodel_name="hr.benefit.type",
        ondelete="restrict",
    )

    name = fields.Char(
        required=True,
    )

    max_dependents = fields.Integer(
        string="Número máximo de dependentes",
    )

    company_percentage = fields.Float(
        string="% Paga pela empresa",
    )

    employee_percentage = fields.Float(
        string="% Paga pelo funcionário",
    )

    dependent_payment_quantity = fields.Monetary(
        string='Quantidade paga pelo dependente',
        currency_field="currency_id"
    )
    
    benefit_fixed_value = fields.Monetary(
        string="Valor fixo do benefício",
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )
