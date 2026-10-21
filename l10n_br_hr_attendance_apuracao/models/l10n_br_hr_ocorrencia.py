# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

# Códigos do campo tipoAusenOuComp do registro 07 do AEJ (Anexo VI).
TIPO_AEJ = [
    ("1", "1 - Descanso Semanal Remunerado (DSR)"),
    ("2", "2 - Falta não justificada"),
    ("3", "3 - Movimento no banco de horas"),
    ("4", "4 - Folga compensatória de feriado"),
]


class L10nBrHrOcorrencia(models.Model):
    """Tipificação das ocorrências de jornada.

    Serve a dois públicos ao mesmo tempo: o AEJ, que só aceita os quatro
    códigos do registro 07, e a folha, que precisa saber se a ocorrência abona
    o dia, desconta DSR ou gera verba. Manter os dois no mesmo cadastro evita
    a tabela paralela que sempre diverge.
    """

    _name = "l10n_br.hr.ocorrencia"
    _description = "Tipo de Ocorrência de Jornada"
    _order = "sequence, name"

    name = fields.Char(required=True)
    codigo = fields.Char(
        required=True,
        help="Código interno da ocorrência, usado nas regras e nos relatórios.",
    )
    sequence = fields.Integer(default=10)
    tipo_aej = fields.Selection(
        selection=TIPO_AEJ,
        string="Código no AEJ",
        help="Deixe vazio quando a ocorrência não deva ser exportada no "
        "registro 07 do AEJ (por exemplo, um atraso já refletido na jornada).",
    )
    abona = fields.Boolean(
        string="Abona o dia",
        help="Ocorrência que justifica a ausência: o dia não vira falta e a "
        "jornada prevista não gera débito.",
    )
    desconta_dsr = fields.Boolean(
        string="Desconta DSR",
        help="Falta injustificada faz perder o repouso semanal remunerado "
        "(Lei 605/49, art. 6º).",
    )
    desconta_dia = fields.Boolean(
        string="Desconta o dia",
        help="Gera desconto do dia na folha.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "codigo_uniq",
            "unique(codigo, company_id)",
            "Já existe uma ocorrência com este código nesta empresa.",
        ),
    ]
