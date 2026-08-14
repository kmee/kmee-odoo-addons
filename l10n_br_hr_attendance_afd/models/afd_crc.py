# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""CRC-16/KERMIT do AFD (Anexo V, item 8 da Portaria MTP 671/2021).

Parâmetros do algoritmo (CRC-16 CCITT-TRUE / KERMIT):

===============  ========
Polinômio        0x1021
Valor inicial    0x0000
XOR final        0x0000
Reflect input    sim
Reflect output   sim
===============  ========

O vetor de conferência da própria Portaria: os 9 caracteres ``123456789``
produzem ``0x2189``, gravados no arquivo como ``2189``.

A base de cálculo é a linha inteira menos os 4 caracteres finais do campo CRC;
o CRLF não entra.
"""

# Tabela pré-calculada do polinômio refletido (0x8408 é 0x1021 espelhado).
_TABELA_CRC = []
for _byte in range(256):
    _valor = _byte
    for _ in range(8):
        if _valor & 1:
            _valor = (_valor >> 1) ^ 0x8408
        else:
            _valor >>= 1
    _TABELA_CRC.append(_valor)


def crc16_kermit(dados):
    """Calcula o CRC-16/KERMIT.

    Args:
        dados: ``bytes`` ou ``str`` (codificado como ISO-8859-1).

    Returns:
        Inteiro de 16 bits.
    """
    if isinstance(dados, str):
        dados = dados.encode("iso-8859-1", errors="replace")
    crc = 0x0000
    for byte in dados:
        crc = (crc >> 8) ^ _TABELA_CRC[(crc ^ byte) & 0xFF]
    return crc & 0xFFFF


def crc16_hex(dados):
    """CRC-16/KERMIT nos 4 caracteres hexadecimais gravados no AFD."""
    return "%04X" % crc16_kermit(dados)


def crc_da_linha(linha):
    """CRC esperado para a linha, calculado sobre tudo menos o campo CRC."""
    return crc16_hex(linha[:-4])


def crc_confere(linha):
    """Compara o CRC gravado no fim da linha com o recalculado.

    A comparação ignora caixa: há relógio que grava o hexadecimal em
    minúsculas, e reprovar por isso seria rejeitar arquivo válido.
    """
    if len(linha) < 5:
        return False
    return linha[-4:].upper() == crc_da_linha(linha)
