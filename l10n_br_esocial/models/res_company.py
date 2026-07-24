# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_esocial_tp_amb = fields.Selection(
        [
            ("1", "1 - Produção"),
            ("2", "2 - Produção Restrita"),
        ],
        string="Ambiente eSocial",
        default="2",
        help="Tipo de ambiente para transmissão dos eventos.",
    )
    l10n_br_esocial_class_trib_id = fields.Many2one(
        "l10n_br.esocial.classificacao.tributaria",
        string="Classificação Tributária",
        help="Classificação tributária do contribuinte conforme Tabela 8 do eSocial.",
    )
    l10n_br_esocial_lotacao_id = fields.Many2one(
        "l10n_br.esocial.lotacao.tributaria",
        string="Lotação Tributária",
        help="Tipo de lotação tributária conforme Tabela 10 do eSocial.",
    )
    l10n_br_esocial_ind_coop = fields.Selection(
        [
            ("0", "0 - Não é cooperativa"),
            ("1", "1 - Cooperativa de trabalho"),
            ("2", "2 - Cooperativa de produção"),
            ("3", "3 - Outras cooperativas"),
        ],
        string="Indicativo de Cooperativa",
        default="0",
    )
    l10n_br_esocial_ind_constr = fields.Selection(
        [
            ("0", "0 - Não é construtora"),
            ("1", "1 - Empresa construtora"),
        ],
        string="Indicativo de Construtora",
        default="0",
    )
    l10n_br_esocial_processo_emissao = fields.Selection(
        [
            ("1", "1 - Aplicativo do empregador"),
            ("2", "2 - Aplicativo governamental (Simplificado)"),
            ("3", "3 - Aplicativo governamental (Web Geral)"),
        ],
        string="Processo de Emissão",
        default="1",
    )
    l10n_br_esocial_cod_lotacao = fields.Char(
        string="Código Lotação",
        size=30,
        help="Código de lotação para agrupamento de trabalhadores.",
    )
    l10n_br_esocial_nm_ctt = fields.Char(
        string="Nome Contato eSocial",
        size=70,
    )
    l10n_br_esocial_cpf_ctt = fields.Char(
        string="CPF Contato eSocial",
        size=11,
    )
    l10n_br_esocial_fone_fixo = fields.Char(
        string="Telefone Fixo eSocial",
        size=13,
    )
    l10n_br_esocial_fone_cel = fields.Char(
        string="Celular eSocial",
        size=13,
    )
    l10n_br_esocial_email = fields.Char(
        string="E-mail eSocial",
        size=60,
    )
