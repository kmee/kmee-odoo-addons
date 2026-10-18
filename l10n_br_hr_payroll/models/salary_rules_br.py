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


# ── INSS - Tabela Progressiva ─────────────────────────────────────────


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


def calc_redutor_irrf(rendimento_bruto, imposto_apurado, faixas):
    """Redutor do IRPF na fonte da Lei 15.270/2025 (vigente desde 01/01/2026).

    A lei NÃO alterou a tabela progressiva mensal (a faixa de isenção continua
    em R$ 2.428,80): a isenção efetiva até R$ 5.000,00 e a redução parcial até
    R$ 7.350,00 operam EXCLUSIVAMENTE por um redutor aplicado **depois** do
    imposto já apurado pela tabela - seja pelo caminho das deduções legais,
    seja pelo desconto simplificado (o mais favorável, ver a regra IRRF).

    Pontos sensíveis da apuração (fonte frequente de erro):

      - A faixa do redutor é definida pelo **rendimento tributável BRUTO do
        mês**, e NÃO pela base de cálculo após INSS/dependentes/pensão.
      - O redutor é **limitado ao imposto apurado**: nunca gera imposto
        negativo nem restituição na folha.
      - Acima do teto da última faixa o corte é **seco** (sem redutor).

    Args:
        rendimento_bruto: Rendimento tributável bruto do mês (ou do 13º,
            quando aplicado ao imposto exclusivo de fonte da gratificação).
        imposto_apurado: Imposto já apurado pela tabela progressiva.
        faixas: Lista ``[(rendimento_max, valor_fixo, fator), ...]`` ascendente,
            resolvida pela competência (ver
            ``l10n_br.hr.payroll.irrf.redutor._tabela``). O redutor da faixa é
            ``valor_fixo - fator * rendimento_bruto``; faixas com ``fator = 0``
            representam redutor fixo (isenção até o teto da faixa). Lista
            VAZIA = competência sem redutor (anterior a 01/2026).

    Returns:
        Valor do redutor em R$ (>= 0), limitado ao ``imposto_apurado``.
    """
    if imposto_apurado <= 0 or not faixas:
        return 0.0
    rendimento = max(rendimento_bruto or 0.0, 0.0)
    for rendimento_max, valor_fixo, fator in faixas:
        if rendimento <= rendimento_max:
            redutor = valor_fixo - fator * rendimento
            return round_money(min(max(redutor, 0.0), imposto_apurado))
    # Acima da última faixa: corte seco, sem redutor.
    return 0.0


def calc_irrf_apos_redutor(rendimento_bruto, imposto_apurado, faixas):
    """Imposto do mês já abatido o redutor da Lei 15.270/2025.

    Conveniência para as regras salariais: encapsula
    ``imposto_apurado - calc_redutor_irrf(...)`` com piso em zero, evitando
    repetir a subtração (e o piso) em cada regra de IRRF.

    Args:
        rendimento_bruto: Rendimento tributável bruto do mês.
        imposto_apurado: Imposto apurado pela tabela progressiva.
        faixas: Faixas do redutor vigentes na competência (vazio = sem redutor).

    Returns:
        Imposto a reter em R$ (>= 0).
    """
    redutor = calc_redutor_irrf(rendimento_bruto, imposto_apurado, faixas)
    return round_money(max(imposto_apurado - redutor, 0.0))


def calc_irrf_mais_favoravel(
    rendimento_tributavel,
    base_legal,
    faixas_irrf,
    desconto_simplificado=0.0,
    faixas_redutor=(),
):
    """IRRF a reter pela forma MAIS FAVORÁVEL ao contribuinte (RF-16).

    Encapsula, num único lugar, as três etapas da apuração do imposto na
    fonte, para que toda apuração (mensal, férias, 13º e rescisão) siga
    exatamente o mesmo caminho:

      1. **Dedução legal** (Lei 9.250/95 art. 4º): imposto sobre a base já
         deduzida de contribuição previdenciária, dependentes e pensão
         alimentícia - a base vem calculada de fora (rubrica ``BASE_IRRF``).
      2. **Desconto simplificado** (Lei 9.250/95, art. 4º, § 2º, incluído pela
         Lei 14.663/2023, art. 6º): no lugar de TODAS as deduções legais,
         abate-se uma parcela fixa do rendimento tributável. Vale para cada
         apuração isoladamente, porque a IN RFB 2.141/2023 inseriu o
         dispositivo em cada base da IN RFB 1.500/2014: art. 13, § 8º (13º
         salário), art. 29, § 5º (férias) e art. 52, § 3º (folha mensal).
         Alcança, portanto, também o imposto exclusivo de fonte do 13º, cuja
         tabela é aplicada em separado dos demais rendimentos.
      3. **Redutor do IRPF** (Lei 9.250/95, art. 3º-A, incluído pela Lei
         15.270/2025, desde 01/2026; para o 13º há dispositivo expresso no
         § 3º do mesmo artigo): aplicado DEPOIS de escolhida a forma mais
         favorável, em função do rendimento tributável BRUTO da apuração.

    A retenção é o MENOR imposto entre (1) e (2): a opção pelo desconto
    simplificado é do contribuinte, e a fonte pagadora deve adotar de ofício
    a forma que resulte no menor imposto, sem exigir declaração do empregado.
    Reter pelo caminho legal quando o simplificado é mais barato significa
    retenção a maior.

    Observação importante: o desconto simplificado substitui as deduções
    legais apenas para efeito de BASE DE CÁLCULO. A pensão alimentícia
    continua sendo integralmente descontada do líquido (é pagamento ao
    alimentando, não dedução tributária).

    Args:
        rendimento_tributavel: Rendimento tributável BRUTO da apuração (antes
            de qualquer dedução). Base do desconto simplificado e do redutor.
        base_legal: Base de cálculo pelo caminho das deduções legais.
        faixas_irrf: Faixas da tabela progressiva vigentes na competência.
        desconto_simplificado: Parcela do desconto simplificado vigente na
            competência (0 = competência anterior a 05/2023, em que só existe
            o caminho das deduções legais).
        faixas_redutor: Faixas do redutor vigentes (vazio = sem redutor).

    Returns:
        Imposto a reter em R$ (>= 0).
    """
    rendimento = max(rendimento_tributavel or 0.0, 0.0)
    imposto = calc_irrf(max(base_legal or 0.0, 0.0), faixas_irrf)
    if desconto_simplificado:
        base_simplificada = max(rendimento - desconto_simplificado, 0.0)
        imposto = min(imposto, calc_irrf(base_simplificada, faixas_irrf))
    return calc_irrf_apos_redutor(rendimento, imposto, faixas_redutor)


def calc_pensao_alimenticia(remuneracao, valor_fixo=0.0, percentual=0.0):
    """Valor efetivo da pensão alimentícia a descontar do líquido.

    Semântica adotada (documentada): o desconto é a SOMA da parcela fixa com
    a parcela percentual sobre a remuneração bruta do mês. Isso cobre os três
    cenários usuais das decisões judiciais:

      - só valor fixo   -> ``percentual = 0``;
      - só percentual   -> ``valor_fixo = 0``;
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
    calendário de feriados por localidade - ver ``l10n_br_resource``). Para a
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

    Regra dos 15 dias (Lei 4.090/62, art. 1º §2º): "a fração igual ou superior
    a 15 (quinze) dias de trabalho será havida como mês integral". A regra vale
    para **qualquer** mês do ano-base - o de admissão E o do desligamento
    (art. 3º, que manda pagar o 13º proporcional na extinção do contrato).

    Por isso o mês da ``data_referencia`` também é medido pelos dias
    efetivamente trabalhados: antes ele era contado como avo cheio, o que
    gerava um avo indevido em rescisões ocorridas antes do dia 15.

    Args:
        data_admissao: Data de admissão (date).
        data_referencia: Último dia considerado (date) - 31/12 no 13º anual,
            data do desligamento no 13º proporcional da rescisão.

    Returns:
        Número de avos (0 a 12).
    """
    import calendar

    avos = 0
    ano = data_referencia.year
    for mes in range(1, data_referencia.month + 1):
        # Meses anteriores à admissão não geram avo.
        if data_admissao.year > ano or (
            data_admissao.year == ano and data_admissao.month > mes
        ):
            continue
        primeiro_dia = (
            data_admissao.day
            if data_admissao.year == ano and data_admissao.month == mes
            else 1
        )
        ultimo_dia = (
            data_referencia.day
            if mes == data_referencia.month
            else calendar.monthrange(ano, mes)[1]
        )
        dias_trabalhados = ultimo_dia - primeiro_dia + 1
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


def calc_salario_familia(remuneracao, num_filhos, faixas, dias_trabalhados=30):
    """Calcula o salário família.

    Args:
        remuneracao: **Salário de contribuição do mês** (remuneração mensal:
            salário + horas extras, adicionais, comissões etc.), que é a base
            legal de enquadramento (Lei 8.213/91 art. 65 c/c Lei 8.212/91
            art. 28) - NÃO o salário contratual.
        num_filhos: Número de filhos elegíveis (até 14 anos ou inválidos).
        faixas: Lista ``[(base_max, valor), ...]`` ascendente, resolvida pela
            competência (ver ``l10n_br.hr.payroll.sal.familia.faixa._tabela``).
        dias_trabalhados: Dias de vigência do contrato no mês (mês comercial de
            30 dias). Nos meses de admissão e de demissão a cota é devida
            proporcionalmente aos dias trabalhados; nos demais meses vale 30
            (cota integral).

    Returns:
        Valor do salário família mensal.
    """
    if num_filhos <= 0:
        return 0.0
    dias = max(0, min(int(dias_trabalhados), 30))
    for limite, valor in faixas:
        if remuneracao <= limite:
            return round_money(num_filhos * valor * dias / 30.0)
    return 0.0


def dias_trabalhados_mes(date_from, date_to, data_admissao=None, data_demissao=None):
    """Dias de vigência do contrato dentro do período do holerite.

    Usado para as verbas devidas proporcionalmente aos dias trabalhados nos
    meses de admissão e de demissão (ex.: cota do salário família). Adota o
    mês comercial de 30 dias, teto usual da folha brasileira.

    Args:
        date_from: Início do período do holerite (date).
        date_to: Fim do período do holerite (date).
        data_admissao: Início do contrato (date) ou ``None``.
        data_demissao: Fim do contrato (date) ou ``None`` (contrato ativo).

    Returns:
        Dias trabalhados no período (int, 0..30).
    """
    inicio = date_from
    if data_admissao and data_admissao > inicio:
        inicio = data_admissao
    fim = date_to
    if data_demissao and data_demissao < fim:
        fim = data_demissao
    if fim < inicio:
        return 0
    return min((fim - inicio).days + 1, 30)
