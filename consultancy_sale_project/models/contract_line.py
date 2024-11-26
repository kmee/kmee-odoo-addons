# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractLine(models.Model):

    _inherit = "contract.line"

    timesheet_invoice_workflow = fields.Selection(
        [
            ("timesheet_no_send", "Não enviar/Faturar direto"),
            ("timesheet_need_approval", "Necessita de Aprovação"),
            ("timesheet_no_approval", "Sem aprovação"),
        ],
        string="Workflow/Faturamento",
    )

    timesheet_report_type = fields.Selection(
        [
            ("timesheet_report_no_send", "Não enviar"),
            ("timesheet_report_daily", "Diário"),
            ("timesheet_report_monthly", "Mensal"),
        ],
        string="Tipo de Relatório",
    )

    timesheet_report_detais = fields.Selection(
        [
            ("timesheet_report_detail_grouped", "Sem detalhes"),
            ("timesheet_report_detail_detailed", "Com detalhes"),
        ],
        string="Formatação no Relatório",
    )
