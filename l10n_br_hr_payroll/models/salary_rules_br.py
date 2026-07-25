# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Funções puras de cálculo da folha de pagamento brasileira.

Estas funções NÃO dependem do ORM Odoo e podem ser testadas
independentemente com pytest puro (sem banco de dados).

Injetadas no contexto das regras salariais via `tools.br.*`.
"""
from decimal import ROUND_HALF_UP, Decimal


def round_money(value, places=2):
    """Arredondamento monetário padrão brasileiro (ROUND_HALF_UP).

    Python round() usa banker's rounding (ROUND_HALF_EVEN) que pode divergir
    do padrão contábil em valores .xx5. Ex: round(2.345, 2) = 2.34 (banker's)
    mas contabilidade BR espera 2.35.

    Args:
        value: Valor a arredondar.
        places: Casas decimais (padrão 2 = centavos).

    Returns:
        Valor arredondado como float.
    """
    d = Decimal(str(value))
    return float(d.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))


# ── INSS — Tabela Progressiva ─────────────────────────────────────────


def calc_inss(salario_bruto, faixas):
    """Calcula o INSS progressivo conforme as faixas vigentes.

    As faixas são resolvidas pela competência do holerite fora daqui
    (ver ``l10n_br.hr.payroll.inss.faixa._tabela``); esta função é pura.

    Args:
        salario_bruto: Salário bruto mensal em R$.
        faixas: Lista ``[(teto, aliquota_fracao), ...]`` ordenada ascendente.
            A incidência é progressiva; o teto de contribuição é a soma das
            faixas até o último ``teto`` (não precisa ser informado à parte).

    Returns:
        Valor do desconto de INSS em R$ (positivo = desconto).
    """
    result = 0.0
    base_anterior = 0.0
    for limite, aliquota in faixas:
        if salario_bruto > base_anterior:
            base_faixa = min(salario_bruto, limite) - base_anterior
            result += base_faixa * aliquota
            base_anterior = limite
        else:
            break
    return round_money(result)


def calc_irrf(base_irrf, faixas):
    """Calcula o IRRF sobre a base de cálculo já deduzida.

    A base deve já ter sido deduzida de INSS, dependentes e pensão.

    Args:
        base_irrf: Base de cálculo do IRRF.
        faixas: Lista ``[(base_max, aliquota_fracao, parcela), ...]`` ascendente,
            resolvida pela competência (ver
            ``l10n_br.hr.payroll.irrf.faixa._tabela``).

    Returns:
        Valor do desconto de IRRF em R$ (sempre >= 0).
    """
    for limite, aliquota, deducao in faixas:
        if base_irrf <= limite:
            result = base_irrf * aliquota - deducao
            return round_money(max(0.0, result))
    return 0.0


def calc_pensao_alimenticia(remuneracao, valor_fixo=0.0, percentual=0.0):
    """Valor efetivo da pensão alimentícia a descontar do líquido.

    Semântica adotada (documentada): o desconto é a SOMA da parcela fixa com
    a parcela percentual sobre a remuneração bruta do mês. Isso cobre os três
    cenários usuais das decisões judiciais:

      - só valor fixo   → ``percentual = 0``;
      - só percentual   → ``valor_fixo = 0``;
      - fixo + percentual (ex.: 1 salário mínimo + 10% do que exceder).

    Args:
        remuneracao: Remuneração bruta do mês (base do percentual).
        valor_fixo: Parcela fixa mensal em R$.
        percentual: Percentual sobre a remuneração em pontos percentuais
            (ex.: ``30.0`` = 30%).

    Returns:
        Valor efetivo da pensão em R$ (>= 0), arredondado.
    """
    valor = (valor_fixo or 0.0) + (remuneracao or 0.0) * (percentual or 0.0) / 100.0
    return round_money(max(0.0, valor))


def dias_dsr(ano, mes):
    """Dias úteis e de descanso (DSR) de um mês.

    Deriva do calendário civil da competência: os domingos são o descanso
    semanal remunerado (DSR) e os demais dias (segunda a sábado) são úteis
    para fins do rateio do desconto de DSR.

    Limitação conhecida: feriados NÃO são computados como DSR (exigiria um
    calendário de feriados por localidade — ver ``l10n_br_resource``). Para a
    maioria das competências o erro é pequeno; quando houver feriado no mês o
    desconto de DSR fica marginalmente subestimado. Documentado como
    pendência de evolução (RF-26).

    Args:
        ano: Ano da competência.
        mes: Mês da competência (1-12).

    Returns:
        Tupla ``(dias_uteis, dsr)``.
    """
    import calendar as _cal
    from datetime import date as _date

    total = _cal.monthrange(ano, mes)[1]
    domingos = sum(1 for d in range(1, total + 1) if _date(ano, mes, d).weekday() == 6)
    return total - domingos, domingos


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

    Regra CLT: fração igual ou superior a 15 dias no mês conta como 1 avo.
    O cálculo considera os dias efetivamente trabalhados no mês de admissão,
    variando conforme o número de dias do mês (28, 29, 30 ou 31).

    Args:
        data_admissao: Data de admissão (date).
        data_referencia: Data de referência (geralmente 31/12).

    Returns:
        Número de avos (0 a 12).
    """
    import calendar

    avos = 0
    ano = data_referencia.year
    for mes in range(1, data_referencia.month + 1):
        if data_admissao.year < ano:
            avos += 1
        elif data_admissao.year == ano and data_admissao.month < mes:
            avos += 1
        elif data_admissao.year == ano and data_admissao.month == mes:
            dias_no_mes = calendar.monthrange(ano, mes)[1]
            dias_trabalhados = dias_no_mes - data_admissao.day + 1
            if dias_trabalhados >= 15:
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
    return round_money(min(limite_6_porcento, valor_vt))


def calc_salario_familia(remuneracao, num_filhos, faixas):
    """Calcula o salário família.

    Args:
        remuneracao: Remuneração mensal usada como base de enquadramento.
        num_filhos: Número de filhos elegíveis (até 14 anos ou inválidos).
        faixas: Lista ``[(base_max, valor), ...]`` ascendente, resolvida pela
            competência (ver ``l10n_br.hr.payroll.sal.familia.faixa._tabela``).

    Returns:
        Valor do salário família mensal.
    """
    if num_filhos <= 0:
        return 0.0
    for limite, valor in faixas:
        if remuneracao <= limite:
            return round_money(num_filhos * valor)
    return 0.0
