import logging
from datetime import date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr

_logger = logging.getLogger(__name__)


class FormulaRecord:
    """Read only view of a record for the SLA formula.

    The formula only needs field values. Handing it the record itself would
    expose the ORM (``record.env``, ``record.sudo()``, ``record.write()``...)
    and the scheduler runs the formula as superuser. Only field names are
    resolved here; relational values are wrapped again, and the wrapped record
    is kept in a name mangled slot that ``safe_eval`` refuses to reach (names
    with a double underscore are forbidden in the expression).
    """

    __slots__ = ("__record",)

    def __init__(self, record):
        self.__record = record

    def __getattr__(self, name):
        record = self.__record
        if name not in record._fields:
            raise AttributeError(name)
        value = record[name]
        if isinstance(value, models.BaseModel):
            if record._fields[name].type == "many2one":
                return FormulaRecord(value)
            return tuple(FormulaRecord(rec) for rec in value)
        return value

    def __bool__(self):
        return bool(self.__record)

    def __len__(self):
        return len(self.__record)


class HelpdeskSLAFormula(models.Model):
    _inherit = "helpdesk.sla"

    use_formula = fields.Boolean(
        "Usar Fórmula Python",
        help="Se marcado, a fórmula Python será usada ao invés do delay padrão",
        groups="helpdesk_mgmt.group_helpdesk_manager",
    )
    sla_deadline_formula = fields.Text(
        "Fórmula Python para Deadline",
        help="Permite definir a data de deadline usando Python.\n"
        "Use 'record' para ler os campos do ticket.\n"
        "O valor retornado deve ser uma data (datetime ou date).\n"
        "Exemplo: record.create_date + timedelta(days=2)",
        groups="helpdesk_mgmt.group_helpdesk_manager",
    )

    @api.constrains("use_formula", "sla_deadline_formula")
    def _check_formula_syntax(self):
        for rule in self.filtered("use_formula"):
            if not rule.sla_deadline_formula:
                continue
            try:
                error = test_python_expr(rule.sla_deadline_formula, mode="eval")
            except NameError as e:
                # forbidden names (double underscore) are raised, not returned
                error = str(e)
            if error:
                raise ValidationError(_("Erro de sintaxe na fórmula Python: %s", error))

    def _get_formula_eval_context(self, ticket):
        return {
            "datetime": datetime,
            "date": date,
            "timedelta": timedelta,
            "relativedelta": relativedelta,
            "record": FormulaRecord(ticket),
        }

    def check_ticket_sla(self, tickets):
        self.ensure_one()
        if not self.use_formula:
            return super().check_ticket_sla(tickets)

        for ticket in tickets:
            try:
                deadline = safe_eval(
                    self.sla_deadline_formula, self._get_formula_eval_context(ticket)
                )

                if not isinstance(deadline, datetime) and isinstance(deadline, date):
                    # plain date: use its start of day to compare with now()
                    deadline = datetime.combine(deadline, time.min)
                ticket.sla_deadline = deadline
                ticket.sla_expired = deadline < datetime.now()

            except Exception as e:
                _logger.error(
                    "Erro ao calcular deadline SLA %s para ticket %s: %s",
                    self.name,
                    ticket.id,
                    str(e),
                )
