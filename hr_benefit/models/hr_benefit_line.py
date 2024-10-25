from odoo import fields, models


class BenefitLine(models.Model):
    _name = "hr.benefit.line"

    benefit_type_id = fields.Many2one(
        comodel_name="hr.benefit.type",
        string="Tipo de Benefício",
        required=True,
        ondelete="restrict",
    )

    contract_id = fields.Many2one(
        comodel_name="hr.contract", string="Contract", required=True, ondelete="cascade"
    )

    dependent_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Dependente"
    )

    beneficiary_id = fields.Many2one(
        comodel_name="res.partner",
        string="Beneficiário"
    )

    benefit_fixed_value = fields.Monetary(
        related='benefit_type_id.benefit_fixed_value',
        currency_field="currency_id",
    )

    company_percentage = fields.Float(
        string="% Paga pela empresa",
        related='benefit_type_id.company_percentage',
    )

    employee_percentage = fields.Float(
        string="% Paga pelo funcionário",
        related='benefit_type_id.employee_percentage',
    )

    dependent_payment_quantity = fields.Monetary(
        string='Quantidade paga pelo dependente',
        related='benefit_type_id.dependent_payment_quantity',
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )