# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_tipo_contrato = fields.Selection(
        selection=[
            ("clt", "CLT"),
            ("estatutario", "Estatutário"),
            ("aprendiz", "Aprendiz"),
            ("temporario", "Temporário"),
        ],
        string="Tipo de Contrato",
        default="clt",
    )
    l10n_br_irrf_dependentes = fields.Integer(
        string="Dependentes IRRF",
        default=0,
    )
    l10n_br_pensao_alimenticia = fields.Float(
        string="Pensão Alimentícia (Valor Fixo)",
        default=0.0,
        help="Parcela fixa mensal de pensão alimentícia determinada "
        "judicialmente. Somada à parcela percentual (se houver).",
    )
    l10n_br_pensao_percentual = fields.Float(
        string="Pensão Alimentícia (% da Remuneração)",
        default=0.0,
        help="Percentual da remuneração bruta destinado à pensão alimentícia "
        "(ex.: 30 = 30%). O valor efetivo descontado é: valor fixo + "
        "percentual sobre a remuneração bruta do mês.",
    )
    l10n_br_molestia_grave = fields.Boolean(
        string="Portador de Moléstia Grave",
        help="Isenção de IRRF conforme Lei 7.713/88",
    )
    l10n_br_cid_molestia = fields.Char(
        string="CID da Moléstia",
    )
    l10n_br_pcd = fields.Boolean(
        string="Pessoa com Deficiência",
    )
    l10n_br_num_filhos_sf = fields.Integer(
        string="Filhos para Salário Família",
        help="Filhos até 14 anos ou inválidos de qualquer idade",
        default=0,
    )
    l10n_br_filhos_invalidos_sf = fields.Integer(
        string="Filhos Inválidos (Salário Família)",
        help="Filhos inválidos de qualquer idade que recebem salário família",
        default=0,
    )
