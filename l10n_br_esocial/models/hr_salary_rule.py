from odoo import fields, models

# Incidência INSS (Contribuição Previdenciária) — eSocial S-1.3
ESOCIAL_COD_INC_CP = [
    ("00", "00 - Não é base de cálculo"),
    ("11", "11 - Base de cálculo das contribuições sociais - Mensal"),
    ("12", "12 - Base de cálculo das contribuições sociais - 13º Salário"),
    ("13", "13 - Exclusiva do empregador - Mensal"),
    ("14", "14 - Exclusiva do empregador - 13º Salário"),
    ("15", "15 - Exclusiva do segurado - Mensal"),
    ("16", "16 - Exclusiva do segurado - 13º Salário"),
    ("21", "21 - Base de cálculo das contribuições sociais - Sal. Maternidade"),
    ("22", "22 - Base de cálculo - Sal. Maternidade 13o"),
    ("25", "25 - Exclusiva do segurado - Sal. Maternidade"),
    ("26", "26 - Exclusiva do segurado - Sal. Maternidade 13o"),
    ("31", "31 - Não é base, mas compõe limite de desconto"),
    ("32", "32 - Já tributada ou isenta de contribuição previdenciária"),
    ("34", "34 - Acordo internacional de previdência"),
    ("35", "35 - Valor descontado do segurado"),
    ("51", "51 - Base de cálculo - Sal. Maternidade complementar"),
    ("91", "91 - Incidência suspensa em decisão judicial - Mensal"),
    ("92", "92 - Incidência suspensa em decisão judicial - 13º Sal."),
    ("93", "93 - Incidência suspensa em decisão judicial - Sal. Maternidade"),
    ("94", "94 - Incidência suspensa em decisão judicial - Sal. Maternidade 13o"),
]

# Incidência IRRF — eSocial S-1.3
ESOCIAL_COD_INC_IRRF = [
    ("00", "00 - Não é base de cálculo (rendimento não tributável)"),
    ("01", "01 - Rendimento não tributável pelo ajuste anual (diárias)"),
    ("09", "09 - Verba transitada pela folha - rendimento tributável"),
    ("11", "11 - Base de cálculo do IRRF - Remuneração mensal"),
    ("12", "12 - Base de cálculo do IRRF - 13° Salário"),
    ("13", "13 - Base de cálculo do IRRF - Férias"),
    ("14", "14 - Base de cálculo do IRRF - PLR"),
    ("15", "15 - Base de cálculo do IRRF - Rendimentos recebidos acumuladamente"),
    ("31", "31 - Retenção do IRRF"),
    ("32", "32 - Retenção do IRRF - 13° Salário"),
    ("33", "33 - Retenção do IRRF - Férias"),
    ("34", "34 - Retenção do IRRF - PLR"),
    ("35", "35 - Retenção do IRRF - RRA"),
    ("41", "41 - Dedução do rendimento tributável do IRRF"),
    ("42", "42 - Dedução do rendimento tributável do IRRF - 13° Salário"),
    ("43", "43 - Dedução do rendimento tributável do IRRF - Férias"),
    ("44", "44 - Dedução do rendimento tributável do IRRF - PLR"),
    ("46", "46 - Dedução do rendimento tributável do IRRF - RRA"),
    ("51", "51 - Isenção do IRRF - Parcela isenta 65 anos"),
    ("52", "52 - Isenção do IRRF - Diárias"),
    ("53", "53 - Isenção do IRRF - Indenização por rescisão"),
    ("54", "54 - Isenção do IRRF - Abono pecuniário de férias"),
    ("55", "55 - Isenção do IRRF - Pensão/Proventos/Reforma por moléstia grave"),
    ("56", "56 - Isenção do IRRF - Lucros e dividendos"),
    ("61", "61 - Dedução cesta básica (Lei 10.925)"),
    ("71", "71 - Rendimento não tributável - PLR"),
    ("72", "72 - Rendimento não tributável - RRA"),
    ("73", "73 - Rendimento não tributável - Outros"),
    ("74", "74 - Depósito judicial"),
    ("75", "75 - Compensação judicial do ano calendário"),
    ("76", "76 - Compensação judicial de anos anteriores"),
    ("77", "77 - Proc. de auto regularização"),
    ("79", "79 - Rendimento isento ou não tributável"),
    ("81", "81 - Base de cálculo do IRRF - Férias complementar"),
    ("82", "82 - Isenção do IRRF - Complem. aposentadoria (poupança)"),
    ("83", "83 - Dedução - Contribuição FAPI"),
    ("91", "91 - Base de cálculo IRRF - Decisão judicial"),
    ("92", "92 - Base de cálculo IRRF 13° - Decisão judicial"),
    ("93", "93 - Base de cálculo IRRF Férias - Decisão judicial"),
    ("94", "94 - Base de cálculo IRRF PLR - Decisão judicial"),
    ("95", "95 - Base de cálculo IRRF RRA - Decisão judicial"),
]

# Incidência FGTS — eSocial S-1.3
ESOCIAL_COD_INC_FGTS = [
    ("00", "00 - Não é base de cálculo do FGTS"),
    ("11", "11 - Base de cálculo do FGTS - Mensal"),
    ("12", "12 - Base de cálculo do FGTS - 13° Salário"),
    ("21", "21 - Base de cálculo do FGTS - Sal. Maternidade"),
    ("91", "91 - Incidência suspensa em decisão judicial"),
]


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    # Identificação da rubrica no eSocial
    l10n_br_esocial_cod_rubr = fields.Char(
        string="Código Rubrica eSocial",
        size=30,
        help="Código atribuído pelo empregador para a rubrica.",
    )
    l10n_br_esocial_ide_tab_rubr = fields.Char(
        string="ID Tabela Rubricas",
        size=8,
        help="Identificador da tabela de rubricas para diferenciação.",
    )
    l10n_br_esocial_nat_rubr_id = fields.Many2one(
        "l10n_br.esocial.natureza.rubrica",
        string="Natureza Rubrica (Tab. 3)",
        help="Natureza da rubrica conforme Tabela 3 do eSocial.",
    )
    l10n_br_esocial_tp_rubr = fields.Selection(
        [
            ("1", "1 - Vencimento/Provento"),
            ("2", "2 - Desconto"),
            ("3", "3 - Informativa"),
            ("4", "4 - Informativa Dedutora"),
        ],
        string="Tipo Rubrica",
        help="Tipo da rubrica conforme eSocial.",
    )

    # Incidências tributárias
    l10n_br_esocial_cod_inc_cp = fields.Selection(
        ESOCIAL_COD_INC_CP,
        string="Incidência INSS",
        help="Código de incidência tributária da rubrica para a Previdência Social.",
    )
    l10n_br_esocial_cod_inc_irrf = fields.Selection(
        ESOCIAL_COD_INC_IRRF,
        string="Incidência IRRF",
        help="Código de incidência tributária da rubrica para o IRRF.",
    )
    l10n_br_esocial_cod_inc_fgts = fields.Selection(
        ESOCIAL_COD_INC_FGTS,
        string="Incidência FGTS",
        help="Código de incidência tributária da rubrica para o FGTS.",
    )
