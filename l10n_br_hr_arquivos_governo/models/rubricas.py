"""Leitura das rubricas (linhas de holerite) usadas nos arquivos do governo.

Centraliza a busca de valores por código de regra salarial para que um
código inexistente NÃO gere silenciosamente um arquivo zerado: sempre que
um holerite não possui nenhuma linha com os códigos esperados, um aviso
explícito é registrado no log.
"""

import logging

_logger = logging.getLogger(__name__)


def normalizar_codigos(codigos):
    """Aceita um código único (str) ou uma coleção de códigos equivalentes."""
    if isinstance(codigos, str):
        return (codigos,)
    return tuple(codigos)


def somar_rubricas(payslips, codigos, origem="Arquivos do Governo"):
    """Soma o total das linhas cujo ``code`` está em ``codigos``.

    :param payslips: recordset de ``hr.payslip`` (pode estar vazio).
    :param codigos: código (str) ou coleção de códigos equivalentes.
    :param origem: identificação do gerador, usada nas mensagens de log.
    :return: tupla ``(total, holerites_sem_a_rubrica)``.

    Quando um holerite não possui nenhuma linha com os códigos informados o
    valor dele é 0,00 e o holerite entra em ``holerites_sem_a_rubrica``; um
    aviso é gravado no log para que o zero não passe despercebido.
    """
    codigos = normalizar_codigos(codigos)
    total = 0.0
    faltantes = payslips.browse()
    for payslip in payslips:
        linhas = payslip.line_ids.filtered(lambda line: line.code in codigos)
        if not linhas:
            faltantes |= payslip
            continue
        total += sum(linhas.mapped("total"))
    if faltantes:
        _logger.warning(
            "%s: nenhuma linha com o(s) código(s) %s encontrada em %d holerite(s) "
            "(%s). O valor foi gravado como ZERO no arquivo — confira os códigos "
            "das regras salariais (hr.salary.rule) da estrutura utilizada.",
            origem,
            "/".join(codigos),
            len(faltantes),
            ", ".join(faltantes.mapped("display_name")[:10]),
        )
    return total, faltantes
