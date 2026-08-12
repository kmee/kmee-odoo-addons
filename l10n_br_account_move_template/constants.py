# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

FISCAL_FIELD = [
    # Impostos próprios
    ("icms_value", "ICMS próprio"),
    ("icmsst_value", "ICMS ST"),
    ("icmssn_credit_value", "Crédito ICMS Simples Nacional"),
    ("icmsfcp_value", "ICMS FCP"),
    ("icmsfcpst_value", "ICMS FCP ST"),
    ("icms_destination_value", "DIFAL - ICMS Destino"),
    ("icms_origin_value", "DIFAL - ICMS Origem"),
    ("ipi_value", "IPI"),
    ("ipi_devol_value", "IPI Devolvido"),
    ("pis_value", "PIS próprio"),
    ("pisst_value", "PIS ST"),
    ("cofins_value", "COFINS própria"),
    ("cofinsst_value", "COFINS ST"),
    ("issqn_value", "ISSQN"),
    ("csll_value", "CSLL própria"),
    ("irpj_value", "IRPJ próprio"),
    ("inss_value", "INSS próprio"),
    ("ii_value", "Imposto de Importação"),
    ("ii_iof_value", "IOF (importação)"),
    ("ii_customhouse_charges", "Despesas Aduaneiras"),
    ("simple_value", "Simples Nacional"),
    # Retenções (Withholding)
    ("pis_wh_value", "PIS retido"),
    ("cofins_wh_value", "COFINS retida"),
    ("csll_wh_value", "CSLL retida"),
    ("irpj_wh_value", "IRRF retido"),
    ("issqn_wh_value", "ISS retido"),
    ("inss_wh_value", "INSS retido"),
    # Valores / Custos
    ("amount_fiscal", "Valor da operação"),
    ("fiscal_amount_untaxed", "Valor sem impostos"),
    ("fiscal_amount_total", "Valor total fiscal"),
    ("financial_total", "Total financeiro"),
    ("discount_value", "Desconto"),
    ("freight_value", "Frete"),
    ("insurance_value", "Seguro"),
    ("other_value", "Outras despesas acessórias"),
    # Reforma Tributária
    ("cbs_value", "CBS"),
    ("ibs_value", "IBS"),
    # Totais computados
    ("amount_tax_included", "Impostos incluídos no preço"),
    ("amount_tax_not_included", "Impostos não incluídos no preço"),
    ("amount_tax_withholding", "Total retenções"),
]

# Fields at item level use product category accounts as fallback
FISCAL_FIELD_ITEM_LEVEL = (
    "amount_fiscal",
    "fiscal_amount_untaxed",
    "icms_value",
    "icmsst_value",
    "ipi_value",
    "ipi_devol_value",
)

# Map fiscal fields to their tax domain for auto-populating tax_domain on items
FISCAL_FIELD_TAX_DOMAIN_MAP = {
    "icms_value": "icms",
    "icmsst_value": "icmsst",
    "icmssn_credit_value": "icmssn",
    "icmsfcp_value": "icmsfcp",
    "icmsfcpst_value": "icmsfcpst",
    "icms_destination_value": "icms",
    "icms_origin_value": "icms",
    "ipi_value": "ipi",
    "ipi_devol_value": "ipi",
    "pis_value": "pis",
    "pisst_value": "pisst",
    "cofins_value": "cofins",
    "cofinsst_value": "cofinsst",
    "issqn_value": "issqn",
    "csll_value": "csll",
    "irpj_value": "irpj",
    "inss_value": "inss",
    "ii_value": "ii",
    "ii_iof_value": "ii",
    "ii_customhouse_charges": "ii",
    "simple_value": "simples",
    "pis_wh_value": "pis_wh",
    "cofins_wh_value": "cofins_wh",
    "csll_wh_value": "csll_wh",
    "irpj_wh_value": "irpj_wh",
    "issqn_wh_value": "issqn_wh",
    "inss_wh_value": "inss_wh",
    "cbs_value": "cbs",
    "ibs_value": "ibs",
}
