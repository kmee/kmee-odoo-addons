from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import ast
import logging

_logger = logging.getLogger(__name__)

class HelpdeskSLAFormula(models.Model):
    _inherit = 'helpdesk.sla'

    use_formula = fields.Boolean(
        'Usar Fórmula Python',
        help='Se marcado, a fórmula Python será usada ao invés do delay padrão'
    )
    sla_deadline_formula = fields.Text(
        'Fórmula Python para Deadline',
        help="Permite definir a data de deadline usando Python.\n"
             "Use 'record' como a instância do ticket.\n"
             "O valor retornado deve ser uma data (datetime ou date).\n"
             "Exemplo: record.create_date + timedelta(days=2)"
    )

    @api.constrains('sla_deadline_formula')
    def _check_formula_syntax(self):
        for rule in self.filtered('use_formula'):
            if not rule.sla_deadline_formula:
                continue
            try:
                ast.parse(rule.sla_deadline_formula)
            except Exception as e:
                raise ValidationError(_(
                    'Erro de sintaxe na fórmula Python: %s', str(e)
                ))

    def check_ticket_sla(self, tickets):
        self.ensure_one()
        if not self.use_formula:
            return super().check_ticket_sla(tickets)

        for ticket in tickets:
            try:
                safe_dict = {
                    'datetime': datetime,
                    'timedelta': timedelta,
                    'relativedelta': relativedelta,
                    'record': ticket,
                }

                deadline = eval(
                    self.sla_deadline_formula,
                    {"__builtins__": {}},
                    safe_dict
                )

                ticket.sla_deadline = deadline
                ticket.sla_expired = deadline < datetime.now()

            except Exception as e:
                _logger.error(
                    "Erro ao calcular deadline SLA %s para ticket %s: %s",
                    self.name, ticket.id, str(e)
                )
