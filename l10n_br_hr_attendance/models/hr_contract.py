# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_br_dispensado_controle_jornada = fields.Boolean(
        string="Dispensado do controle de jornada",
        help="Art. 62 da CLT: atividade externa incompatível com fixação de "
        "horário, cargo de gestão ou teletrabalho por produção/tarefa. "
        "Contratos assim não geram apuração nem entram no AEJ.",
    )
    l10n_br_motivo_dispensa_jornada = fields.Selection(
        selection=[
            ("externo", "I - atividade externa incompatível"),
            ("gestao", "II - cargo de gestão"),
            ("teletrabalho", "III - teletrabalho por produção ou tarefa"),
        ],
        string="Enquadramento do art. 62",
    )
    l10n_br_registro_por_excecao = fields.Boolean(
        string="Registro por exceção",
        help="Art. 74, § 4º da CLT: registro apenas das exceções à jornada "
        "contratual, mediante acordo individual escrito, convenção ou acordo "
        "coletivo. Exige o acordo anexado ao contrato.",
    )
    l10n_br_rep_id = fields.Many2one(
        comodel_name="l10n_br.hr.rep",
        string="REP padrão",
        help="Registrador em que este contrato marca ponto. Define o "
        "estabelecimento usado no AFD e no AEJ.",
    )

    def _l10n_br_sujeito_controle_jornada(self):
        """Contratos que devem ter jornada apurada e entrar no AEJ."""
        return self.filtered(lambda c: not c.l10n_br_dispensado_controle_jornada)
