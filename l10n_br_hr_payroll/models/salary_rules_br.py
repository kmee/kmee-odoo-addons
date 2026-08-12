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


# ── ENCARGOS PATRONAIS (CPP, RAT/GILRAT, terceiros) ───────────────────

# Alíquota da contribuição previdenciária patronal (CPP) sobre a folha:
# 20% do total das remunerações (Lei 8.212/91, art. 22, I). Sem teto - ao
# contrário da contribuição do empregado, que para no teto do RGPS.
ALIQUOTA_CPP = 0.20

# FGTS (Lei 8.036/90, art. 15): 8% da remuneração; 2% no contrato de
# aprendizagem (art. 15 §7º). Não é tributo, mas é custo do empregador e é
# devido em QUALQUER regime tributário, inclusive no Simples Nacional.
ALIQUOTA_FGTS = 0.08
ALIQUOTA_FGTS_APRENDIZ = 0.02

# Regimes do campo ``tax_framework`` (l10n_br_fiscal) que são Simples Nacional.
TAX_FRAMEWORK_SIMPLES = ("1", "2", "4")

# Anexos do Simples Nacional cuja CPP patronal NÃO está incluída no DAS e
# portanto é recolhida por fora (LC 123/2006, art. 18, §5º-C).
SIMPLES_ANEXO_CPP_POR_FORA = ("iv",)


def aliquota_rat_ajustado(rat, fap):
    """RAT ajustado = RAT x FAP, em pontos percentuais.

    O RAT (1%, 2% ou 3%, conforme o grau de risco do CNAE preponderante do
    estabelecimento) é a contribuição para o financiamento dos benefícios
    decorrentes de riscos ambientais do trabalho (Lei 8.212/91, art. 22, II).
    O FAP (Fator Acidentário de Prevenção, 0,5 a 2,0) multiplica o RAT
    (Lei 10.666/2003, art. 10, regulamentado pelo Decreto 3.048/99,
    art. 202-A), resultando na alíquota efetivamente devida - o "RAT
    ajustado", que é justamente o valor declarado no eSocial (S-1005,
    ``aliqRatAjust``).

    Args:
        rat: Alíquota RAT em pontos percentuais (1.0, 2.0 ou 3.0).
        fap: Fator acidentário (0,5 a 2,0).

    Returns:
        Alíquota ajustada em pontos percentuais, com 4 casas decimais (o FAP
        é publicado com 4 casas, ex.: 0,7639 x 3 = 2,2917).
    """
    return round_money((rat or 0.0) * (fap or 0.0), 4)


def aliquota_fgts(aprendiz=False):
    """Alíquota do FGTS do empregador (fração), 2% no aprendiz."""
    return ALIQUOTA_FGTS_APRENDIZ if aprendiz else ALIQUOTA_FGTS


def aliquota_cpp_cprb(perc_cpp, perc_contrib_nao_desonerada=0.0):
    """CPP sobre a folha (fração) na transição da desoneração (CPRB).

    Empresas dos setores dos arts. 7º e 8º da Lei 12.546/2011 que optam pela
    CPRB substituem a CPP dos **incisos I e III** do art. 22 da Lei 8.212/91
    por uma contribuição sobre a receita bruta. A Lei 14.973/2024 (arts. 9º-A
    e 9º-B da Lei 12.546/2011) transformou a substituição total num regime
    híbrido e decrescente até a extinção: a cada ano uma PROPORÇÃO da CPP
    volta a incidir sobre a folha (25% em 2025, 50% em 2026, 75% em 2027,
    100% a partir de 2028).

    Atividade concomitante (mista): quando a empresa também aufere receita
    NÃO desonerada, a substituição alcança apenas a parte proporcional à
    receita desonerada. Essa proporção é dado de COMPETÊNCIA (muda mês a mês
    com o faturamento) e é declarada no eSocial no S-1280
    (``percRedContrib``), por isso entra aqui como parâmetro e não numa tabela
    por vigência.

    **Direção do percRedContrib (erro clássico):** o campo do S-1280 é o
    percentual A QUE a contribuição patronal fica REDUZIDA, ou seja, a razão
    ``receita NÃO desonerada / receita total``. Desoneração TOTAL informa
    ZERO, não 100. Daí a fórmula, com ``q = percRedContrib / 100``::

        CPP = 20% x folha x [q + perc_cpp x (1 - q)]

    Sem atividade concomitante (``q = 0``) a alíquota efetiva é
    ``perc_cpp x 20%`` (em 2026: 50% x 20% = 10%). Com ``q = 1`` (nada
    desonerado) a CPP é integral.

    Note ainda que o fator de transição do ano (os 50% de 2026) NÃO entra no
    valor transmitido: o eSocial aplica a proporção do art. 9º-A por regra
    interna (NT S-1.3 nº 02/2024). O fator existe aqui apenas para o cálculo
    interno da folha, da provisão e da contabilização.

    ATENÇÃO (armadilha central da reoneração): a proporção alcança SOMENTE a
    CPP dos incisos I e III. O RAT/GILRAT (inciso II), o adicional de
    aposentadoria especial e as contribuições de terceiros continuam
    **INTEGRAIS** - nunca aplicar ``perc_cpp`` a eles.

    Args:
        perc_cpp: Proporção da CPP devida sobre a folha no ano, em pontos
            percentuais (0 a 100), vinda da tabela por vigência
            (``l10n_br.hr.payroll.cprb.transicao``).
        perc_contrib_nao_desonerada: ``percRedContrib`` do S-1280 em pontos
            percentuais: proporção da receita NÃO desonerada sobre a receita
            bruta total. 0 = substituição integral (sem atividade
            concomitante); 100 = nenhuma receita desonerada no mês.

    Returns:
        Alíquota efetiva da CPP sobre a folha, como fração.
    """
    q = min(max((perc_contrib_nao_desonerada or 0.0) / 100.0, 0.0), 1.0)
    proporcao = min(max((perc_cpp or 0.0) / 100.0, 0.0), 1.0)
    return ALIQUOTA_CPP * (q + proporcao * (1.0 - q))


def aliquotas_patronais(
    tax_framework="3",
    simples_anexo=False,
    rat=1.0,
    fap=1.0,
    perc_terceiros=0.0,
    aprendiz=False,
    cprb_perc_cpp=None,
    cprb_perc_contrib_nao_desonerada=0.0,
):
    """Alíquotas dos encargos patronais conforme o REGIME TRIBUTÁRIO.

    Encargo patronal é CUSTO do empregador: não é descontado do empregado e
    não entra no líquido. O que varia radicalmente de uma empresa para outra
    é *quais* encargos são devidos, e isso é função do regime:

      - **Lucro Real / Presumido** (regime normal, ``tax_framework = '3'``):
        CPP 20% (art. 22, I) + RAT ajustado (art. 22, II) + terceiros pelo
        código FPAS. Encargo cheio.
      - **Simples Nacional, anexos I, II, III e V**: a CPP e o RAT estão
        incluídos no DAS (LC 123/2006, art. 13, VI) e as contribuições de
        terceiros são expressamente dispensadas (art. 13, §3º). NÃO se gera
        CPP, RAT nem terceiros - apenas o FGTS, que não é tributo e é devido
        em qualquer anexo (Súmula 353 do STJ).
      - **Simples Nacional, anexo IV** (construção civil, vigilância,
        limpeza): o DAS não inclui a CPP, que é recolhida por fora na forma
        do art. 22 da Lei 8.212/91 (LC 123/2006, art. 18, §5º-C) - logo CPP
        **e RAT** são devidos; terceiros seguem dispensados pelo art. 13, §3º.
      - **CPRB** (desoneração em transição): quando informada
        ``cprb_perc_cpp``, a CPP é reduzida proporcionalmente (ver
        ``aliquota_cpp_cprb``); RAT e terceiros continuam integrais.

    O FGTS é devido em todos os casos e vem sempre preenchido, para que o
    chamador possa provisionar encargos sobre férias/13º sem ter de repetir
    a regra do aprendiz.

    Args:
        tax_framework: Regime tributário da empresa (``res.company``
            ``tax_framework`` do l10n_br_fiscal: '1'/'2'/'4' = Simples,
            '3' = regime normal).
        simples_anexo: Anexo do Simples ('i'..'v'), quando optante. Aceita o
            anexo da atividade do contrato, que pode diferir do anexo
            preponderante da empresa (atividade concomitante).
        rat: Alíquota RAT do estabelecimento em pontos percentuais.
        fap: Fator acidentário de prevenção.
        perc_terceiros: Alíquota de terceiros/outras entidades do código FPAS
            da lotação tributária, em pontos percentuais (indústria,
            FPAS 507: 5,8). É parâmetro, e não constante, porque a
            composição varia por enquadramento (o SEBRAE, em especial, muda
            conforme o porte/atividade - Anexo III da IN RFB 2.110/2022).
        aprendiz: Contrato de aprendizagem (FGTS 2%).
        cprb_perc_cpp: Proporção da CPP devida sobre a folha no ano da
            competência, em pontos percentuais, quando a empresa é optante
            pela CPRB. ``None`` = não optante (CPP integral).
        cprb_perc_contrib_nao_desonerada: ``percRedContrib`` do S-1280
            (proporção da receita NÃO desonerada; 0 = desoneração total).

    Returns:
        Dicionário de FRAÇÕES: ``cpp``, ``rat``, ``terceiros``, ``fgts``,
        ``total_patronal`` (cpp + rat + terceiros, sem FGTS) e
        ``total_com_fgts``.
    """
    fgts = aliquota_fgts(aprendiz)
    anexo = (simples_anexo or "").lower()
    simples = (tax_framework or "3") in TAX_FRAMEWORK_SIMPLES

    cpp = rat_ajustado = terceiros = 0.0
    if not simples or anexo in SIMPLES_ANEXO_CPP_POR_FORA:
        cpp = ALIQUOTA_CPP
        if cprb_perc_cpp is not None:
            cpp = aliquota_cpp_cprb(cprb_perc_cpp, cprb_perc_contrib_nao_desonerada)
        rat_ajustado = aliquota_rat_ajustado(rat, fap) / 100.0
        # Terceiros: só no regime normal. Todo optante do Simples é
        # dispensado (LC 123/2006, art. 13, §3º), inclusive no anexo IV.
        if not simples:
            terceiros = (perc_terceiros or 0.0) / 100.0

    total_patronal = cpp + rat_ajustado + terceiros
    return {
        "cpp": cpp,
        "rat": rat_ajustado,
        "terceiros": terceiros,
        "fgts": fgts,
        "total_patronal": total_patronal,
        "total_com_fgts": total_patronal + fgts,
    }


# ── PROVISÕES DE FÉRIAS E 13º ─────────────────────────────────────────


def calc_provisao_ferias(remuneracao, avos=1.0):
    """Provisão mensal de férias com o 1/3 constitucional.

    O direito a férias é adquirido mês a mês (CLT art. 130) e o encargo deve
    ser reconhecido por competência, não no pagamento (Lei 6.404/76, art. 177;
    CPC 33 - Benefícios a Empregados, que trata das ausências remuneradas
    acumuláveis). Por isso a folha provisiona a cada mês 1/12 da remuneração
    acrescido de 1/3 (CF art. 7º, XVII), o que equivale a
    ``remuneração x 4 / 36``. Para fins fiscais, a dedutibilidade da provisão
    de férias com os encargos está no art. 342 do RIR/2018.

    Args:
        remuneracao: Remuneração do mês (base da provisão).
        avos: Avos a provisionar no mês (1 = mês integral).

    Returns:
        Valor da provisão em R$.
    """
    return round_money((remuneracao or 0.0) / 12.0 * (4.0 / 3.0) * (avos or 0.0))


def calc_provisao_decimo_terceiro(remuneracao, avos=1.0):
    """Provisão mensal do 13º salário: 1/12 da remuneração por avo.

    Mesma razão da provisão de férias (competência): a gratificação natalina
    é devida na proporção de 1/12 por mês trabalhado (Lei 4.090/62, art. 1º);
    a dedutibilidade de 1/12 com os encargos está no art. 343 do RIR/2018.
    """
    return round_money((remuneracao or 0.0) / 12.0 * (avos or 0.0))


def calc_encargos_sobre_provisao(provisao, aliquota_total, perc_base_isenta=0.0):
    """Encargos patronais incidentes sobre uma provisão.

    A provisão de férias e de 13º carrega os mesmos encargos da remuneração
    que ela antecipa: CPP, RAT ajustado, terceiros e FGTS - cada um conforme
    o regime tributário (ver ``aliquotas_patronais``). No Simples Nacional
    dos anexos I, II, III e V a provisão leva **somente FGTS**, porque a CPP
    e o RAT estão no DAS e terceiros são dispensados.

    Segregação de férias gozadas x indenizadas (evita superprovisionar): o
    terço de férias GOZADAS integra a base patronal (STF, Tema 985), mas as
    férias INDENIZADAS (e o respectivo terço) não sofrem contribuição
    previdenciária (Lei 8.212/91, art. 28, §9º, "d") nem FGTS (Lei 8.036/90,
    art. 15, §6º). Como no momento da provisão ainda não se sabe qual parte
    será gozada e qual será indenizada, a parcela esperada de indenização
    entra como percentual paramétrico e é excluída da base dos encargos.

    Args:
        provisao: Valor provisionado no mês.
        aliquota_total: Soma das alíquotas aplicáveis (fração), tipicamente
            ``aliquotas_patronais(...)["total_com_fgts"]``.
        perc_base_isenta: Percentual da provisão que se espera pagar como
            verba indenizatória, sem encargos (0 a 100). Zero = toda a
            provisão será gozada/paga com encargos.

    Returns:
        Valor dos encargos sobre a provisão em R$.
    """
    isenta = min(max((perc_base_isenta or 0.0) / 100.0, 0.0), 1.0)
    base = (provisao or 0.0) * (1.0 - isenta)
    return round_money(base * (aliquota_total or 0.0))


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
