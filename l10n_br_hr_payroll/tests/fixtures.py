# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tabelas fiscais de 2024 como fixtures para os testes unitários puros.

As funções de cálculo (``salary_rules_br``) passaram a receber as faixas
resolvidas pela competência. Nos testes puros passamos explicitamente as
faixas de 2024 — os mesmos valores carregados em
``data/l10n_br.hr.payroll.*.csv`` para a vigência 2024.
"""

# INSS 2024 (2024-01-01..2024-12-31): [(teto, aliquota_fracao), ...]
FAIXAS_INSS_2024 = [
    (1412.00, 0.075),
    (2666.68, 0.09),
    (4000.03, 0.12),
    (7786.02, 0.14),
]

# IRRF 2024 (vigência 2024-02-01..2025-04-30):
# [(base_max, aliquota_fracao, parcela_deduzir), ...]
FAIXAS_IRRF_2024 = [
    (2259.20, 0.000, 0.00),
    (2826.65, 0.075, 169.44),
    (3751.05, 0.150, 381.44),
    (4664.68, 0.225, 662.77),
    (9999999999.0, 0.275, 896.00),
]

# Salário família 2024 (faixa única vigente): [(base_max, valor), ...]
FAIXAS_SF_2024 = [
    (1819.26, 62.04),
]
