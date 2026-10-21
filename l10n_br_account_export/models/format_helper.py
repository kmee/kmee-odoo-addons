# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Formatacao de campo para arquivos de intercambio contabil.

Os layouts dos sistemas de escritorio de contabilidade se dividem em poucas
familias, e todas se resolvem com as funcoes deste modulo:

- **posicional**: campo de largura fixa, alinhado a esquerda (texto) ou a
  direita (numero), preenchido com espaco ou zero;
- **delimitado**: campos separados por virgula, ponto e virgula ou pipe;
- **hibrido**: delimitado, mas com cada campo tambem em largura fixa (o IGNIS
  faz isso).

Sao funcoes puras, sem ORM, para poderem ser testadas isoladamente e
reaproveitadas por qualquer adapter.
"""

ALIGN_LEFT = "left"
ALIGN_RIGHT = "right"


def clean_text(value, size=None, sep=None):
    """Texto seguro para arquivo de intercambio.

    Remove quebras de linha (que partiriam o registro) e, quando informado, o
    proprio separador. Trunca no tamanho do campo, porque layout posicional nao
    admite campo maior que o previsto.
    """
    text = value or ""
    if not isinstance(text, str):
        text = str(text)
    if sep:
        text = text.replace(sep, " ")
    text = " ".join(text.split())
    if size:
        text = text[:size]
    return text


def pad(value, size, align=ALIGN_LEFT, fill=" "):
    """Campo de largura fixa.

    Trunca o que exceder: um campo maior que o previsto desloca todos os
    seguintes e corrompe o arquivo inteiro, o que e pior que perder o excesso.
    """
    text = "" if value is None else str(value)
    text = text[:size]
    if align == ALIGN_RIGHT:
        return text.rjust(size, fill)
    return text.ljust(size, fill)


def zero_pad(value, size):
    """Numero alinhado a direita com zeros a esquerda."""
    return pad(value, size, align=ALIGN_RIGHT, fill="0")


def format_amount(amount, decimal_sep=",", decimals=2, thousands_sep=""):
    """Valor monetario no padrao dos layouts contabeis.

    O valor sai sempre positivo: os layouts indicam o lado (debito ou credito)
    por campo ou por coluna, nunca por sinal.
    """
    value = abs(float(amount or 0.0))
    spec = ",." + str(decimals) + "f"
    text = format(value, spec)  # 1,234.56
    # o formato nativo usa virgula para milhar e ponto para decimal
    text = text.replace(",", "\x00").replace(".", decimal_sep)
    text = text.replace("\x00", thousands_sep)
    return text


def amount_cents(amount, size=None):
    """Valor em centavos, sem separador (padrao de layout posicional)."""
    cents = int(round(abs(float(amount or 0.0)) * 100))
    text = str(cents)
    return zero_pad(text, size) if size else text


def format_date(value, mask="%d/%m/%Y"):
    """Data no formato do layout. Vazio quando nao ha data."""
    if not value:
        return ""
    return value.strftime(mask)


def only_digits(value):
    """Apenas os digitos, que e como os layouts esperam CNPJ, CPF e CEP."""
    return "".join(c for c in (value or "") if c.isdigit())


def join_delimited(fields, sep, wrap=None, leading=False, trailing=False):
    """Monta um registro delimitado.

    ``wrap`` envolve cada campo (o Alterdata usa aspas duplas); ``leading`` e
    ``trailing`` acrescentam o separador nas bordas (o Dominio faz isso).
    """
    parts = [("" if f is None else str(f)) for f in fields]
    if wrap:
        parts = [f"{wrap}{p}{wrap}" for p in parts]
    line = sep.join(parts)
    if leading:
        line = sep + line
    if trailing:
        line = line + sep
    return line
