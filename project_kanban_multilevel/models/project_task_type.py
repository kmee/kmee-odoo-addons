from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    has_sub_stages = fields.Boolean(
        string="Possui sub-estágios",
        default=False,
        help="Se ativo, o estágio é dividido em 'Fazendo' e 'Feito'.",
    )
    wip_limit = fields.Integer(
        string="WIP Limit",
        default=0,
        help="0 = sem limite. Número máximo de cards neste estágio.",
    )
    wip_limit_type = fields.Selection(
        [("count", "Contagem de cards"), ("size", "Soma de pontos")],
        string="Tipo de WIP",
        default="count",
    )
    area_type = fields.Selection(
        [
            ("requested", "Solicitado"),
            ("progress", "Em progresso"),
            ("done", "Concluído"),
        ],
        string="Área do workflow",
        default="progress",
    )
