import calendar
from datetime import date

from odoo import fields, models

MESES = [
    ("1", "Janeiro"),
    ("2", "Fevereiro"),
    ("3", "Março"),
    ("4", "Abril"),
    ("5", "Maio"),
    ("6", "Junho"),
    ("7", "Julho"),
    ("8", "Agosto"),
    ("9", "Setembro"),
    ("10", "Outubro"),
    ("11", "Novembro"),
    ("12", "Dezembro"),
]


class HrPayslipGenerator(models.TransientModel):
    _name = "hr.payslip.generator"
    _description = "Gerador de Holerites em Lote"

    contract_id = fields.Many2one(
        comodel_name="hr.contract",
        string="Contrato",
        required=True,
        domain="[('state', '=', 'open')]",
    )
    mes_do_ano = fields.Selection(
        selection=MESES,
        string="Mês Inicial",
        required=True,
        default=lambda self: str(date.today().month),
    )
    ano = fields.Integer(
        required=True,
        default=lambda self: date.today().year,
    )
    quantity = fields.Integer(
        string="Quantidade de Holerites",
        required=True,
        default=12,
    )
    payslip_ids = fields.Many2many(
        comodel_name="hr.payslip",
        string="Holerites Gerados",
        readonly=True,
    )

    def action_generate(self):
        """Gera holerites mensais consecutivos a partir do mês/ano selecionado."""
        self.ensure_one()
        contract = self.contract_id
        employee = contract.employee_id
        struct = contract.struct_id

        payslips = self.env["hr.payslip"]
        month = int(self.mes_do_ano)
        year = self.ano

        for _i in range(self.quantity):
            last_day = calendar.monthrange(year, month)[1]
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)

            payslip = self.env["hr.payslip"].create(
                {
                    "employee_id": employee.id,
                    "contract_id": contract.id,
                    "struct_id": struct.id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "name": "Holerite %s %02d/%d" % (employee.name, month, year),
                }
            )
            payslip.compute_sheet()
            payslips |= payslip

            month += 1
            if month > 12:
                month = 1
                year += 1

        self.payslip_ids = payslips

        return {
            "type": "ir.actions.act_window",
            "name": "Holerites Gerados",
            "res_model": "hr.payslip",
            "view_mode": "tree,form",
            "domain": [("id", "in", payslips.ids)],
            "target": "current",
        }
