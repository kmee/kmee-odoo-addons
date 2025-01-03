from odoo import api, fields, models


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

    dependent_ids = fields.Many2many(comodel_name="res.partner", string="Dependente")

    beneficiary_id = fields.Many2one(comodel_name="res.partner", string="Beneficiário")

    benefit_fixed_value = fields.Monetary(
        string="Valor fixo do benefício",
        currency_field="currency_id",
    )

    company_percentage = fields.Float(
        string="% Paga pela empresa",
        related="benefit_type_id.company_percentage",
    )

    employee_percentage = fields.Float(
        string="% Paga pelo funcionário",
        related="benefit_type_id.employee_percentage",
    )

    dependent_employee_percentage = fields.Float(
        string="% Paga pelo funcionário (Por dependente)",
        related="benefit_type_id.dependent_employee_percentage",
    )

    dependent_company_percentage = fields.Float(
        string="% Paga pela empresa (Por dependente)",
        related="benefit_type_id.dependent_company_percentage",
    )

    dependent_payment_value = fields.Monetary(
        string="Valor pago por dependente",
        related="benefit_type_id.dependent_payment_value",
    )

    employee_payment_value = fields.Monetary(
        string="Valor pago pelo funcionário",
        compute="_compute_payment_values",
        store=True,
    )

    company_payment_value = fields.Monetary(
        string="Valor pago pela empresa",
        compute="_compute_payment_values",
        store=True,
    )

    total_benefit_value = fields.Monetary(
        string="Valor total",
        compute="_compute_total_benefit_value",
        store=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    @api.onchange("benefit_type_id")
    def _onchange_benefit_type_id(self):
        """
        Atualiza o valor padrão do benefício ao selecionar.
        O valor pode ser personalizado na linha agora.
        """
        for record in self:
            if record.benefit_type_id:
                record.benefit_fixed_value = record.benefit_type_id.benefit_fixed_value

    @api.depends(
        "benefit_fixed_value",
        "company_percentage",
        "employee_percentage",
        "dependent_ids",
        "dependent_payment_value",
    )
    def _compute_payment_values(self):
        for record in self:
            fixed_value = record.benefit_fixed_value or 0.0
            total_dependents = len(record.dependent_ids)
            total_dependent_cost = total_dependents * (
                record.dependent_payment_value or 0.0
            )

            fixed_company_share = (
                fixed_value * (record.company_percentage or 0.0)
            ) / 100.0
            fixed_employee_share = (
                fixed_value * (record.employee_percentage or 0.0)
            ) / 100.0

            dependent_company_share = (
                total_dependent_cost * (record.dependent_company_percentage or 0.0)
            ) / 100.0
            dependent_employee_share = (
                total_dependent_cost * (record.dependent_employee_percentage or 0.0)
            ) / 100.0

            record.company_payment_value = fixed_company_share + dependent_company_share
            record.employee_payment_value = (
                fixed_employee_share + dependent_employee_share
            )

    @api.depends("benefit_fixed_value", "dependent_ids", "dependent_payment_value")
    def _compute_total_benefit_value(self):
        for record in self:
            fixed_value = record.benefit_fixed_value or 0.0
            total_dependents = len(record.dependent_ids)
            total_dependent_cost = total_dependents * (
                record.dependent_payment_value or 0.0
            )
            record.total_benefit_value = fixed_value + total_dependent_cost
