import calendar
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Teto sensato para geração em lote (ex.: 5 anos de competências mensais).
MAX_QUANTITY = 60

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

    @api.constrains("quantity")
    def _check_quantity(self):
        """Valida a quantidade solicitada (positiva e dentro do teto)."""
        for wizard in self:
            if wizard.quantity <= 0:
                raise UserError(_("A quantidade de holerites deve ser maior que zero."))
            if wizard.quantity > MAX_QUANTITY:
                raise UserError(
                    _(
                        "A quantidade de holerites (%(qty)s) excede o limite "
                        "de %(max)s competências por geração.",
                        qty=wizard.quantity,
                        max=MAX_QUANTITY,
                    )
                )

    def action_generate(self):
        """Gera holerites mensais consecutivos a partir do mês/ano selecionado.

        Pula competências que já possuem holerite para o mesmo contrato
        (evitando duplicar folhas — o que duplicaria encargos em SEFIP/DIRF).
        """
        self.ensure_one()
        contract = self.contract_id
        employee = contract.employee_id
        struct = contract.struct_id

        payslips = self.env["hr.payslip"]
        skipped = 0
        month = int(self.mes_do_ano)
        year = self.ano

        for _i in range(self.quantity):
            last_day = calendar.monthrange(year, month)[1]
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)

            existing = self.env["hr.payslip"].search(
                [
                    ("contract_id", "=", contract.id),
                    ("state", "!=", "cancel"),
                    ("date_from", "<=", date_to),
                    ("date_to", ">=", date_from),
                ],
                limit=1,
            )
            if existing:
                skipped += 1
                _logger.info(
                    "Gerador: competência %02d/%d já possui holerite (%s) "
                    "para o contrato %s — geração ignorada.",
                    month,
                    year,
                    existing.name,
                    contract.name,
                )
            else:
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
        if skipped:
            _logger.info(
                "Gerador: %d competência(s) ignorada(s) por já possuírem "
                "holerite; %d holerite(s) criado(s).",
                skipped,
                len(payslips),
            )

        return {
            "type": "ir.actions.act_window",
            "name": "Holerites Gerados",
            "res_model": "hr.payslip",
            "view_mode": "tree,form",
            "domain": [("id", "in", payslips.ids)],
            "target": "current",
        }
