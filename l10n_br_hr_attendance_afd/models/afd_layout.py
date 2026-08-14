# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Leiaute do AFD - Arquivo Fonte de Dados.

Módulo puro (sem ORM) com o leiaute posicional do **Anexo V da Portaria MTP
671/2021** e do **Anexo I da Portaria 1.510/2009**, que continua legal para os
REP-C certificados antes de 10/02/2022 (art. 96 da 671).

Manter o leiaute fora do ORM tem uma razão prática: parser e gerador podem ser
testados sem banco, e a tabela de campos vira documentação executável - quando
a posição de um campo muda, muda em um lugar só.

Convenções do Anexo V:

- texto ISO-8859-1, uma linha por registro, terminada em CRLF;
- registros ordenados por NSR, sem linhas em branco;
- campos preenchidos da esquerda, completando com espaço à direita;
- data ``AAAA-MM-dd``; data e hora ``AAAA-MM-ddThh:mm:00ZZZZZ`` (fuso obrigatório);
- CRC-16/KERMIT nos registros 1 a 5; SHA-256 no registro 7.
"""

from collections import namedtuple

ENCODING_AFD = "iso-8859-1"
TERMINADOR_LINHA = "\r\n"
VERSAO_LEIAUTE_671 = "003"

# Texto literal que substitui a assinatura no rodapé quando ela vai em arquivo
# .p7s destacado (Anexo V, bloco de assinatura digital).
ASSINATURA_EM_ARQUIVO = "ASSINATURA_DIGITAL_EM_ARQUIVO_P7S"

Campo = namedtuple("Campo", "nome inicio tamanho tipo")


def _campos(*definicoes):
    """Monta a lista de campos calculando as posições em sequência."""
    campos = []
    posicao = 0
    for nome, tamanho, tipo in definicoes:
        campos.append(Campo(nome, posicao, tamanho, tipo))
        posicao += tamanho
    return campos


# --------------------------------------------------------------------------
# Portaria 671/2021 - Anexo V
# --------------------------------------------------------------------------

LEIAUTE_671 = {
    "1": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("tipo_identificador_empregador", 1, "N"),
        ("cnpj_cpf_empregador", 14, "N"),
        ("cno_caepf", 14, "N"),
        ("razao_social", 150, "A"),
        ("identificador_rep", 17, "N"),
        ("data_inicial", 10, "D"),
        ("data_final", 10, "D"),
        ("data_hora_geracao", 24, "DH"),
        ("versao_leiaute", 3, "N"),
        ("tipo_identificador_fabricante", 1, "N"),
        ("cnpj_cpf_fabricante", 14, "N"),
        ("modelo", 30, "A"),
        ("crc", 4, "A"),
    ),
    "2": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_hora_gravacao", 24, "DH"),
        ("cpf_responsavel", 14, "N"),
        ("tipo_identificador_empregador", 1, "N"),
        ("cnpj_cpf_empregador", 14, "N"),
        ("cno_caepf", 14, "N"),
        ("razao_social", 150, "A"),
        ("local_prestacao", 100, "A"),
        ("crc", 4, "A"),
    ),
    "3": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "A"),
        ("data_hora_marcacao", 24, "DH"),
        ("cpf", 12, "N"),
        ("crc", 4, "A"),
    ),
    "4": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_hora_antes", 24, "DH"),
        ("data_hora_ajustada", 24, "DH"),
        ("cpf_responsavel", 11, "N"),
        ("crc", 4, "A"),
    ),
    "5": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_hora_gravacao", 24, "DH"),
        ("operacao", 1, "A"),
        ("cpf", 12, "N"),
        ("nome", 52, "A"),
        ("dados_identificacao", 4, "A"),
        ("cpf_responsavel", 11, "N"),
        ("crc", 4, "A"),
    ),
    "6": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_hora_gravacao", 24, "DH"),
        ("tipo_evento", 2, "N"),
    ),
    "7": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "A"),
        ("data_hora_marcacao", 24, "DH"),
        ("cpf", 12, "N"),
        ("data_hora_gravacao", 24, "DH"),
        ("coletor", 2, "N"),
        ("offline", 1, "N"),
        ("hash", 64, "A"),
    ),
    "9": _campos(
        ("nsr", 9, "N"),
        ("qtd_tipo_2", 9, "N"),
        ("qtd_tipo_3", 9, "N"),
        ("qtd_tipo_4", 9, "N"),
        ("qtd_tipo_5", 9, "N"),
        ("qtd_tipo_6", 9, "N"),
        ("qtd_tipo_7", 9, "N"),
        ("tipo_registro", 1, "N"),
    ),
}

# Registros que carregam CRC-16 (item 8 do Anexo V).
TIPOS_COM_CRC = ("1", "2", "3", "4", "5")

# Registros que são marcação de ponto.
TIPOS_MARCACAO_671 = ("3", "7")


# --------------------------------------------------------------------------
# Portaria 1.510/2009 - Anexo I (leiaute legado, art. 96 da 671)
# --------------------------------------------------------------------------

LEIAUTE_1510 = {
    "1": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("tipo_identificador_empregador", 1, "N"),
        ("cnpj_cpf_empregador", 14, "N"),
        ("cei", 12, "N"),
        ("razao_social", 150, "A"),
        ("numero_fabricacao", 17, "N"),
        ("data_inicial", 8, "D8"),
        ("data_final", 8, "D8"),
        ("data_geracao", 8, "D8"),
        ("hora_geracao", 4, "H"),
    ),
    "2": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_gravacao", 8, "D8"),
        ("hora_gravacao", 4, "H"),
        ("tipo_identificador_empregador", 1, "N"),
        ("cnpj_cpf_empregador", 14, "N"),
        ("cei", 12, "N"),
        ("razao_social", 150, "A"),
        ("local_prestacao", 100, "A"),
    ),
    "3": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "A"),
        ("data_marcacao", 8, "D8"),
        ("hora_marcacao", 4, "H"),
        ("pis", 12, "N"),
    ),
    "4": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_antes", 8, "D8"),
        ("hora_antes", 4, "H"),
        ("data_ajustada", 8, "D8"),
        ("hora_ajustada", 4, "H"),
    ),
    "5": _campos(
        ("nsr", 9, "N"),
        ("tipo_registro", 1, "N"),
        ("data_gravacao", 8, "D8"),
        ("hora_gravacao", 4, "H"),
        ("operacao", 1, "A"),
        ("pis", 12, "N"),
        ("nome", 52, "A"),
    ),
    "9": _campos(
        ("nsr", 9, "N"),
        ("qtd_tipo_2", 9, "N"),
        ("qtd_tipo_3", 9, "N"),
        ("qtd_tipo_4", 9, "N"),
        ("qtd_tipo_5", 9, "N"),
        ("tipo_registro", 1, "N"),
    ),
}

TIPOS_MARCACAO_1510 = ("3",)

LEIAUTES = {
    "671": LEIAUTE_671,
    "1510": LEIAUTE_1510,
}


def tamanho_registro(leiaute, tipo):
    """Soma dos campos do tipo de registro no leiaute informado."""
    campos = LEIAUTES[leiaute].get(tipo)
    if not campos:
        return 0
    ultimo = campos[-1]
    return ultimo.inicio + ultimo.tamanho


def identifica_tipo(linha):
    """Descobre o tipo do registro pela posição 10 (ou pelo trailer).

    O trailer não tem o tipo na posição 10 - ele começa com ``999999999`` e
    guarda o "9" no fim da linha, então precisa ser reconhecido pelo prefixo.
    """
    if linha.startswith("999999999"):
        return "9"
    if len(linha) < 10:
        return None
    return linha[9]


def fatia(linha, leiaute, tipo, nome_campo):
    """Extrai um campo pela posição, sem espaços de preenchimento."""
    for campo in LEIAUTES[leiaute][tipo]:
        if campo.nome == nome_campo:
            return linha[campo.inicio : campo.inicio + campo.tamanho].strip()
    raise KeyError(
        "Campo %s não existe no registro tipo %s do leiaute %s"
        % (nome_campo, tipo, leiaute)
    )


def monta_registro(leiaute, tipo, valores):
    """Serializa um registro posicional.

    Numéricos vão alinhados à direita com zeros; alfanuméricos à esquerda com
    espaços, como manda o item 7 do Anexo V. O campo ``crc`` é deixado por
    conta do chamador, que calcula sobre o registro já montado.
    """
    partes = []
    for campo in LEIAUTES[leiaute][tipo]:
        valor = str(valores.get(campo.nome, "") or "")
        if len(valor) > campo.tamanho:
            valor = valor[: campo.tamanho]
        if campo.tipo == "N":
            partes.append(valor.rjust(campo.tamanho, "0"))
        else:
            partes.append(valor.ljust(campo.tamanho, " "))
    return "".join(partes)
