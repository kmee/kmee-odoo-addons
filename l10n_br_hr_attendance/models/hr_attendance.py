# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrAttendance(models.Model):
    """Sessão de trabalho (par entrada/saída) derivada das marcações.

    O ``hr.attendance`` permanece como a visão do Odoo sobre a jornada - é ele
    que alimenta as horas extras do core e o módulo de multiplicador. A
    diferença é a procedência: quando o par vem de marcações de REP, os dois
    lados apontam para os registros originais e a sessão não pode ser editada
    à mão sem que a origem fique visível.
    """

    _inherit = "hr.attendance"

    l10n_br_marcacao_entrada_id = fields.Many2one(
        comodel_name="l10n_br.hr.marcacao",
        string="Marcação de entrada",
        ondelete="set null",
        copy=False,
    )
    l10n_br_marcacao_saida_id = fields.Many2one(
        comodel_name="l10n_br.hr.marcacao",
        string="Marcação de saída",
        ondelete="set null",
        copy=False,
    )
    l10n_br_origem = fields.Selection(
        selection=[
            ("rep", "Marcação de REP"),
            ("manual", "Lançamento manual"),
        ],
        string="Origem",
        compute="_compute_l10n_br_origem",
        store=True,
        help="Sessões derivadas de marcação de REP têm lastro no AFD; as "
        "manuais precisam de justificativa no espelho de ponto.",
    )
    l10n_br_seq_par = fields.Integer(
        string="Par entrada/saída",
        help="Ordem do par no dia, usada no registro 05 do AEJ.",
    )

    @api.depends("l10n_br_marcacao_entrada_id", "l10n_br_marcacao_saida_id")
    def _compute_l10n_br_origem(self):
        for rec in self:
            rec.l10n_br_origem = "rep" if rec.l10n_br_marcacao_entrada_id else "manual"
