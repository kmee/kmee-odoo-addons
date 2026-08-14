# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Regras de apuração de jornada da CLT, em funções puras.

Tudo aqui trabalha com ``datetime`` e ``float`` - nada de ORM. O motivo é o
mesmo que levou a folha a ter o ``salary_rules_br.py``: regra de cálculo
trabalhista é o tipo de código que precisa de teste barato, exaustivo e
legível, e que um dia vai ser conferido linha a linha contra um parecer.

Referências: arts. 58, 58-A, 59, 66, 71 e 73 da CLT e Súmulas 366 e 172 do TST.
"""

from datetime import datetime, time, timedelta

# Art. 58, § 1º: até 5 minutos por marcação, limitados a 10 no dia.
TOLERANCIA_POR_MARCACAO = 5
TOLERANCIA_DIARIA = 10

# Art. 73, § 1º: a hora noturna urbana vale 52min30s.
HORA_NOTURNA_MINUTOS = 52.5
FATOR_HORA_NOTURNA = 60.0 / HORA_NOTURNA_MINUTOS  # 8/7

# Art. 73: horário noturno urbano das 22h às 5h.
NOTURNO_INICIO = time(22, 0)
NOTURNO_FIM = time(5, 0)

# Art. 71: intervalo mínimo para jornada acima de 6h e para a faixa de 4h a 6h.
INTRAJORNADA_MINIMA_ACIMA_6H = 60
INTRAJORNADA_MINIMA_ATE_6H = 15
# Art. 611-A, III: norma coletiva pode reduzir o mínimo até 30 minutos.
INTRAJORNADA_MINIMA_NEGOCIADA = 30

# Art. 66: intervalo mínimo entre duas jornadas.
INTERJORNADA_MINIMA_HORAS = 11


def parear_marcacoes(marcacoes):
    """Forma pares entrada/saída na ordem cronológica.

    A Portaria exige número par de marcações no dia. Quando sobra uma, ela é
    devolvida como ímpar em vez de o motor inventar uma saída: fabricar
    marcação é justamente o que o art. 74 proíbe.

    Args:
        marcacoes: lista de ``datetime`` (ordenada ou não).

    Returns:
        Tupla ``(pares, impar)``, onde ``pares`` é lista de ``(entrada, saida)``
        e ``impar`` é o ``datetime`` sem par, ou ``None``.
    """
    ordenadas = sorted(marcacoes)
    pares = []
    for indice in range(0, len(ordenadas) - 1, 2):
        pares.append((ordenadas[indice], ordenadas[indice + 1]))
    impar = ordenadas[-1] if len(ordenadas) % 2 else None
    return pares, impar


def minutos_trabalhados(pares):
    """Soma dos intervalos de trabalho, em minutos."""
    return sum((saida - entrada).total_seconds() / 60.0 for entrada, saida in pares)


def minutos_intervalo(pares):
    """Soma dos intervalos ENTRE pares (a intrajornada efetivamente gozada)."""
    total = 0.0
    for anterior, seguinte in zip(pares, pares[1:]):
        total += (seguinte[0] - anterior[1]).total_seconds() / 60.0
    return total


def aplica_tolerancia(minutos_previstos, minutos_realizados, limite_diario=None):
    """Tolerância do art. 58, § 1º, com a regra da Súmula 366 do TST.

    A tolerância NÃO é franquia: se a variação total do dia passa de 10
    minutos, computa-se o tempo integral, não o excedente. Abaixo disso, a
    variação simplesmente não existe para efeito de jornada - nem a favor do
    empregado, nem do empregador.

    Args:
        minutos_previstos: jornada contratual do dia, em minutos.
        minutos_realizados: minutos efetivamente trabalhados.
        limite_diario: limite em minutos; ``None`` usa o legal de 10.

    Returns:
        Tupla ``(extra, deficit)`` em minutos, já com a tolerância aplicada.
    """
    limite = TOLERANCIA_DIARIA if limite_diario is None else limite_diario
    variacao = minutos_realizados - minutos_previstos
    if abs(variacao) <= limite:
        return 0.0, 0.0
    if variacao > 0:
        return variacao, 0.0
    return 0.0, -variacao


def variacao_dentro_da_tolerancia_por_marcacao(previstas, realizadas):
    """Confere o limite de 5 minutos POR marcação, além do limite diário.

    Args:
        previstas: lista de ``datetime`` esperados pela jornada contratual.
        realizadas: lista de ``datetime`` efetivamente marcados.

    Returns:
        ``True`` quando nenhuma marcação isolada varia mais que 5 minutos.
    """
    if len(previstas) != len(realizadas):
        return False
    return all(
        abs((real - previsto).total_seconds()) / 60.0 <= TOLERANCIA_POR_MARCACAO
        for previsto, real in zip(sorted(previstas), sorted(realizadas))
    )


def _intervalo_noturno_do_dia(referencia):
    """Janela 22h-5h que COMEÇA no dia da referência."""
    inicio = datetime.combine(referencia.date(), NOTURNO_INICIO)
    fim = datetime.combine(referencia.date() + timedelta(days=1), NOTURNO_FIM)
    return inicio, fim


def minutos_noturnos(pares):
    """Minutos trabalhados dentro da janela noturna (art. 73).

    A janela cruza a meia-noite, então cada par é confrontado com a janela do
    próprio dia e com a do dia anterior - quem entra às 21h e sai às 6h tem
    trecho noturno nas duas.
    """
    total = 0.0
    for entrada, saida in pares:
        # As datas-base entram num conjunto: entrada e saída no mesmo dia
        # apontariam para a mesma janela e o trecho seria contado duas vezes.
        bases = {
            (entrada - timedelta(days=1)).date(),
            entrada.date(),
            saida.date(),
        }
        for base in bases:
            inicio, fim = _intervalo_noturno_do_dia(datetime.combine(base, time()))
            comeco = max(entrada, inicio)
            termino = min(saida, fim)
            if termino > comeco:
                total += (termino - comeco).total_seconds() / 60.0
    return total


def horas_noturnas_computadas(minutos_reais, usar_hora_reduzida=True):
    """Converte minutos noturnos cronológicos em horas noturnas legais.

    Com a hora reduzida do art. 73, § 1º, cada 52min30s de relógio equivalem a
    uma hora de jornada - por isso o fator 8/7.
    """
    horas = minutos_reais / 60.0
    return horas * FATOR_HORA_NOTURNA if usar_hora_reduzida else horas


def intrajornada_minima(minutos_jornada, minimo_negociado=None):
    """Intervalo mínimo devido para a jornada do dia (art. 71).

    Args:
        minutos_jornada: duração da jornada realizada, em minutos.
        minimo_negociado: mínimo fixado em convenção ou acordo coletivo, que
            pela regra do art. 611-A, III não pode ser inferior a 30 minutos.

    Returns:
        Minutos de intervalo exigidos.
    """
    if minutos_jornada <= 4 * 60:
        return 0
    if minutos_jornada <= 6 * 60:
        return INTRAJORNADA_MINIMA_ATE_6H
    if minimo_negociado:
        return max(int(minimo_negociado), INTRAJORNADA_MINIMA_NEGOCIADA)
    return INTRAJORNADA_MINIMA_ACIMA_6H


def intrajornada_suprimida(minutos_jornada, minutos_gozados, minimo_negociado=None):
    """Período de intervalo suprimido, indenizável pelo art. 71, § 4º.

    Depois da Reforma paga-se APENAS o período suprimido com acréscimo de 50%,
    e a verba é indenizatória - não o intervalo inteiro, como na redação
    anterior.
    """
    devido = intrajornada_minima(minutos_jornada, minimo_negociado)
    if not devido:
        return 0.0
    return max(0.0, devido - minutos_gozados)


def interjornada_respeitada(saida_anterior, entrada_seguinte):
    """Art. 66: 11 horas consecutivas entre duas jornadas."""
    if not saida_anterior or not entrada_seguinte:
        return True
    descanso = (entrada_seguinte - saida_anterior).total_seconds() / 3600.0
    return descanso >= INTERJORNADA_MINIMA_HORAS


def dsr_sobre_horas_extras(valor_horas_extras, dias_uteis, dias_repouso):
    """Reflexo das horas extras no DSR (Lei 605/49, art. 7º; Súmula 172 TST).

    A conta legal é ``total de HE / dias úteis x dias de repouso``. Dias úteis
    zerados devolvem zero em vez de estourar: mês sem dia útil é dado
    inconsistente, não motivo para derrubar a folha inteira.
    """
    if not dias_uteis:
        return 0.0
    return valor_horas_extras / dias_uteis * dias_repouso


def desconto_dsr_por_falta(valor_dia, semanas_com_falta, dias_repouso_semana=1):
    """Perda do DSR da semana em que houve falta injustificada (Lei 605/49).

    O desconto é POR SEMANA, não por falta: duas faltas na mesma semana fazem
    perder um repouso, não dois. Quem conta as semanas é o chamador, que
    conhece o calendário; aqui só se multiplica.
    """
    if semanas_com_falta <= 0:
        return 0.0
    return valor_dia * semanas_com_falta * dias_repouso_semana


def semanas_com_falta(datas_de_falta):
    """Quantidade de semanas distintas atingidas por falta injustificada.

    Usa a semana ISO (segunda a domingo), que é a que o DSR acompanha.
    """
    return len(
        {(data.isocalendar()[0], data.isocalendar()[1]) for data in datas_de_falta}
    )


def classifica_horas_extras(minutos_extras, faixas):
    """Distribui os minutos extras nas faixas configuradas, em ordem.

    Args:
        minutos_extras: total de minutos excedentes no dia.
        faixas: lista de dicionários com ``limite_minutos`` (``None`` para
            "o que sobrar") e ``multiplicador``.

    Returns:
        Lista de ``(minutos, multiplicador)`` na ordem das faixas.
    """
    restante = max(0.0, minutos_extras)
    distribuicao = []
    for faixa in faixas:
        if restante <= 0:
            break
        limite = faixa.get("limite_minutos")
        alocado = restante if limite is None else min(restante, limite)
        if alocado > 0:
            distribuicao.append((alocado, faixa["multiplicador"]))
            restante -= alocado
    return distribuicao
