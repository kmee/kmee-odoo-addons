# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Funções puras de cálculo da folha de pagamento brasileira.

Estas funções NÃO dependem do ORM Odoo e podem ser testadas
independentemente com pytest puro (sem banco de dados).

Injetadas no contexto das regras salariais via `tools.br.*`.
"""


# ── INSS — Tabela Progressiva ─────────────────────────────────────────

INSS_TABELAS = {
    2024: {
        "faixas": [
            (1412.00, 0.075),
            (2666.68, 0.09),
            (4000.03, 0.12),
            (7786.02, 0.14),
        ],
        "teto": 908.86,
    },
}

# ── IRRF — Tabela Progressiva ─────────────────────────────────────────

IRRF_TABELAS = {
    2024: [
        (2259.20, 0.000, 0.00),
        (2826.65, 0.075, 169.44),
        (3751.05, 0.150, 381.44),
        (4664.68, 0.225, 662.77),
        (float("inf"), 0.275, 896.00),
    ],
}

IRRF_DEDUCAO_DEPENDENTE = 189.59

# ── Salário Família — Tabela 2024 ─────────────────────────────────────

SALARIO_FAMILIA_TABELA_2024 = [
    (1869.34, 62.04),
    (2903.98, 43.84),
]

# ── Salário Mínimo ────────────────────────────────────────────────────

SALARIO_MINIMO = {
    2024: 1412.00,
}


def calc_inss(salario_bruto, ano=2024):
    """Calcula o INSS progressivo conforme a tabela do ano.

    Args:
        salario_bruto: Salário bruto mensal em R$.
        ano: Ano de referência para a tabela.

    Returns:
        Valor do desconto de INSS em R$ (positivo = desconto).
    """
    tabela = INSS_TABELAS.get(ano, INSS_TABELAS[2024])
    result = 0.0
    base_anterior = 0.0
    for limite, aliquota in tabela["faixas"]:
        if salario_bruto > base_anterior:
            base_faixa = min(salario_bruto, limite) - base_anterior
            result += base_faixa * aliquota
            base_anterior = limite
        else:
            break
    return round(min(result, tabela["teto"]), 2)


def calc_irrf(base_irrf, ano=2024):
    """Calcula o IRRF sobre a base de cálculo já deduzida.

    A base deve já ter sido deduzida de INSS, dependentes e pensão.

    Args:
        base_irrf: Base de cálculo do IRRF.
        ano: Ano de referência.

    Returns:
        Valor do desconto de IRRF em R$ (sempre >= 0).
    """
    tabela = IRRF_TABELAS.get(ano, IRRF_TABELAS[2024])
    for limite, aliquota, deducao in tabela:
        if base_irrf <= limite:
            result = base_irrf * aliquota - deducao
            return round(max(0.0, result), 2)
    return 0.0


def calc_ferias_dias(faltas):
    """Retorna dias de férias conforme faltas injustificadas (CLT art. 130).

    Args:
        faltas: Número de faltas injustificadas no período aquisitivo.

    Returns:
        Dias de férias a que o funcionário tem direito.
    """
    if faltas <= 5:
        return 30
    elif faltas <= 14:
        return 24
    elif faltas <= 23:
        return 18
    elif faltas <= 32:
        return 12
    return 0


def calc_decimo_avos(data_admissao, data_referencia):
    """Calcula os avos do 13º salário.

    Args:
        data_admissao: Data de admissão (date).
        data_referencia: Data de referência (geralmente 31/12).

    Returns:
        Número de avos (0 a 12).
    """
    avos = 0
    ano = data_referencia.year
    for mes in range(1, data_referencia.month + 1):
        if data_admissao.year < ano:
            avos += 1
        elif data_admissao.year == ano and data_admissao.month < mes:
            avos += 1
        elif data_admissao.year == ano and data_admissao.month == mes:
            if data_admissao.day <= 15:
                avos += 1
    return min(avos, 12)


def calc_vt(salario, valor_vt):
    """Calcula o desconto de Vale-Transporte do empregado.

    Máximo de 6% do salário, limitado ao valor do VT.

    Args:
        salario: Salário mensal.
        valor_vt: Valor total do VT mensal.

    Returns:
        Valor do desconto de VT.
    """
    limite_6_porcento = salario * 0.06
    return round(min(limite_6_porcento, valor_vt), 2)


def calc_salario_familia(salario_bruto, num_filhos, ano=2024):
    """Calcula o salário família.

    Args:
        salario_bruto: Salário bruto mensal.
        num_filhos: Número de filhos elegíveis (até 14 anos ou inválidos).
        ano: Ano de referência.

    Returns:
        Valor do salário família mensal.
    """
    if num_filhos <= 0:
        return 0.0
    tabela = SALARIO_FAMILIA_TABELA_2024
    for limite, valor in tabela:
        if salario_bruto <= limite:
            return round(num_filhos * valor, 2)
    return 0.0
