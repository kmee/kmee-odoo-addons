import ast
import logging
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskSLAFormula(models.Model):
    _inherit = "helpdesk.sla"

    use_formula = fields.Boolean(
        "Usar Fórmula Python",
        help="Se marcado, a fórmula Python será usada ao invés do delay padrão",
    )
    sla_deadline_formula = fields.Text(
        "Fórmula Python para Deadline",
        help="Permite definir a data de deadline usando Python.\n"
        "Use 'record' como a instância do ticket.\n"
        "O valor retornado deve ser uma data (datetime ou date).\n"
        "Exemplo: record.create_date + timedelta(days=2)",
    )

    @api.constrains("sla_deadline_formula")
    def _check_formula_syntax(self):
        for rule in self.filtered("use_formula"):
            if not rule.sla_deadline_formula:
                continue
            try:
                ast.parse(rule.sla_deadline_formula)
            except Exception as e:
                raise ValidationError(
                    _("Erro de sintaxe na fórmula Python: %s", str(e))
                ) from e

    def _eval_deadline_formula(self, ticket):
        """Evaluate the formula for a ticket and return a datetime (or False)."""
        self.ensure_one()
        safe_dict = {
            "datetime": datetime,
            "timedelta": timedelta,
            "relativedelta": relativedelta,
            "record": ticket,
        }
        try:
            deadline = eval(  # pylint: disable=eval-used
                self.sla_deadline_formula, {"__builtins__": {}}, safe_dict
            )
        except Exception as e:
            _logger.error(
                "Error computing SLA deadline %s for ticket %s: %s",
                self.name,
                ticket.id,
                str(e),
            )
            return False
        if isinstance(deadline, date) and not isinstance(deadline, datetime):
            deadline = datetime.combine(deadline, datetime.max.time())
        return deadline or False
