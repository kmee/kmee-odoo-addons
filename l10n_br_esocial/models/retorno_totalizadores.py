# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Leitura dos eventos totalizadores devolvidos pelo eSocial.

Os totalizadores (S-5001, S-5002, S-5003, S-5011, S-5012 e S-5013) não são
gerados pelo empregador: eles voltam dentro do retorno do evento periódico, no
grupo ``tot``, e são a fonte oficial do que o governo apurou.

A leitura vive aqui, e não na esociallib, porque a versão publicada da
biblioteca (0.1.3) cobre a geração e a transmissão, mas não o retorno dos
totalizadores. Depender de um módulo inexistente deixava o consumo desligado em
silêncio, e a conferência da competência lia zero como se fosse ausência de
divergência.

O XML é lido por nome local do elemento: cada evento totalizador tem namespace
próprio (evtBasesTrab, evtCS, evtIrrf...), e casar por namespace só criaria uma
lista de constantes para manter a cada versão do leiaute.
"""

import logging
from dataclasses import dataclass, field

from lxml import etree

_logger = logging.getLogger(__name__)

# Nome local do elemento do evento -> tipo do totalizador.
EVENTOS_TOTALIZADORES = {
    "evtBasesTrab": "S-5001",
    "evtIrrfBenef": "S-5002",
    "evtBasesFGTS": "S-5003",
    "evtCS": "S-5011",
    "evtIrrf": "S-5012",
    "evtFGTS": "S-5013",
}


@dataclass
class LinhaTotalizador:
    """Um valor apurado pelo governo, com o contexto que o identifica."""

    grupo: str
    codigo: str = None
    descricao: str = None
    valor: float = 0.0
    matricula: str = None
    cod_categ: str = None
    cod_lotacao: str = None
    tp_insc: str = None
    nr_insc: str = None
    ind_13: str = None
    per_ref: str = None


@dataclass
class Totalizador:
    """Um evento totalizador lido do retorno."""

    evento: str
    per_apur: str = None
    ind_apuracao: str = None
    nr_rec_arq_base: str = None
    cpf_trab: str = None
    ind_exist_info: str = None
    id_evento: str = None
    xml: str = None
    linhas: list = field(default_factory=list)


def _nome(elemento):
    return etree.QName(elemento).localname


def _texto(pai, nome):
    """Texto do primeiro descendente com o nome local informado."""
    if pai is None:
        return None
    for elemento in pai.iter():
        if _nome(elemento) == nome and elemento.text:
            return elemento.text.strip()
    return None


def _valor(texto):
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0.0


def _valores_do_grupo(elemento, prefixos=("vr", "vlr")):
    """Pares (nome, valor) dos filhos diretos que carregam valor monetário.

    O leiaute nomeia todo valor com prefixo ``vr`` ou ``vlr``, o que evita ter
    de listar campo a campo e sobreviver melhor a acréscimos de versão.
    """
    return [
        (_nome(filho), _valor(filho.text))
        for filho in elemento
        if _nome(filho).startswith(prefixos) and filho.text
    ]


def _parse_s5001(evt, totalizador):
    """S-5001: bases e valores por trabalhador."""
    for info_cp_calc in evt.iter():
        if _nome(info_cp_calc) != "infoCpCalc":
            continue
        tp_cr = _texto(info_cp_calc, "tpCR")
        for nome, valor in _valores_do_grupo(info_cp_calc):
            totalizador.linhas.append(
                LinhaTotalizador(
                    grupo="info_cp_calc",
                    codigo=tp_cr,
                    descricao=nome,
                    valor=valor,
                )
            )

    for ide_estab_lot in evt.iter():
        if _nome(ide_estab_lot) != "ideEstabLot":
            continue
        contexto = {
            "tp_insc": _texto(ide_estab_lot, "tpInsc"),
            "nr_insc": _texto(ide_estab_lot, "nrInsc"),
            "cod_lotacao": _texto(ide_estab_lot, "codLotacao"),
        }
        for categ in ide_estab_lot.iter():
            if _nome(categ) != "infoCategIncid":
                continue
            contexto_categ = dict(
                contexto,
                matricula=_texto(categ, "matricula"),
                cod_categ=_texto(categ, "codCateg"),
            )
            for base in categ.iter():
                nome_base = _nome(base)
                if nome_base == "infoBaseCS":
                    totalizador.linhas.append(
                        LinhaTotalizador(
                            grupo="base_cs",
                            codigo=_texto(base, "tpValor"),
                            descricao="valor",
                            valor=_valor(_texto(base, "valor")),
                            ind_13=_texto(base, "ind13"),
                            **contexto_categ,
                        )
                    )
                elif nome_base == "basePisPasep":
                    totalizador.linhas.append(
                        LinhaTotalizador(
                            grupo="base_pis_pasep",
                            descricao="valor",
                            valor=_valor(_texto(base, "valor")),
                            ind_13=_texto(base, "ind13"),
                            **contexto_categ,
                        )
                    )
                elif nome_base == "calcTerc":
                    tp_cr = _texto(base, "tpCR")
                    for nome, valor in _valores_do_grupo(base):
                        totalizador.linhas.append(
                            LinhaTotalizador(
                                grupo="calc_terc",
                                codigo=tp_cr,
                                descricao=nome,
                                valor=valor,
                                **contexto_categ,
                            )
                        )


def _linhas_consolidadas_s5011(evt, totalizador):
    """Grupos consolidados do S-5011: contribuição do segurado e do contribuinte."""
    for elemento in evt.iter():
        nome_elemento = _nome(elemento)
        if nome_elemento == "infoCPSeg":
            for nome, valor in _valores_do_grupo(elemento):
                totalizador.linhas.append(
                    LinhaTotalizador(grupo="cp_seg", descricao=nome, valor=valor)
                )
        elif nome_elemento == "infoCRContrib":
            tp_cr = _texto(elemento, "tpCR")
            for nome, valor in _valores_do_grupo(elemento):
                totalizador.linhas.append(
                    LinhaTotalizador(
                        grupo="cr_contrib",
                        codigo=tp_cr,
                        descricao=nome,
                        valor=valor,
                    )
                )


def _linhas_cr_estab(ide_estab, totalizador, tp_insc, nr_insc):
    """Códigos de receita por estabelecimento."""
    for cr_estab in ide_estab.iter():
        if _nome(cr_estab) != "infoCREstab":
            continue
        tp_cr = _texto(cr_estab, "tpCR")
        for nome, valor in _valores_do_grupo(cr_estab):
            totalizador.linhas.append(
                LinhaTotalizador(
                    grupo="cr_estab",
                    codigo=tp_cr,
                    descricao=nome,
                    valor=valor,
                    tp_insc=tp_insc,
                    nr_insc=nr_insc,
                )
            )


def _linhas_bases_lotacao(ide_estab, totalizador, tp_insc, nr_insc):
    """Bases de contribuição por lotação e categoria."""
    grupos = {"basesCp": "base_cp", "basesCp13": "base_cp13"}
    for lotacao in ide_estab.iter():
        if _nome(lotacao) != "ideLotacao":
            continue
        cod_lotacao = _texto(lotacao, "codLotacao")
        for bases_remun in lotacao.iter():
            if _nome(bases_remun) != "basesRemun":
                continue
            cod_categ = _texto(bases_remun, "codCateg")
            for bases in bases_remun:
                grupo = grupos.get(_nome(bases))
                if not grupo:
                    continue
                for nome, valor in _valores_do_grupo(bases):
                    totalizador.linhas.append(
                        LinhaTotalizador(
                            grupo=grupo,
                            descricao=nome,
                            valor=valor,
                            cod_categ=cod_categ,
                            cod_lotacao=cod_lotacao,
                            tp_insc=tp_insc,
                            nr_insc=nr_insc,
                        )
                    )


def _parse_s5011(evt, totalizador):
    """S-5011: contribuições sociais consolidadas do fechamento."""
    _linhas_consolidadas_s5011(evt, totalizador)
    for ide_estab in evt.iter():
        if _nome(ide_estab) != "ideEstab":
            continue
        tp_insc = _texto(ide_estab, "tpInsc")
        nr_insc = _texto(ide_estab, "nrInsc")
        _linhas_cr_estab(ide_estab, totalizador, tp_insc, nr_insc)
        _linhas_bases_lotacao(ide_estab, totalizador, tp_insc, nr_insc)


def _parse_cr_irrf(evt, totalizador, per_ref=None):
    """Grupos de código de receita do IRRF (S-5002 e S-5012)."""
    for elemento in evt.iter():
        grupo, campo_codigo = {
            "infoCRMen": ("cr_men", "CRMen"),
            "infoCRDia": ("cr_dia", "CRDia"),
            "consolidApurMen": ("cr_men", "CRMen"),
            "consolidApurDia": ("cr_dia", "CRDia"),
        }.get(_nome(elemento), (None, None))
        if not grupo:
            continue
        codigo = _texto(elemento, campo_codigo)
        for nome, valor in _valores_do_grupo(elemento):
            totalizador.linhas.append(
                LinhaTotalizador(
                    grupo=grupo,
                    codigo=codigo,
                    descricao=nome,
                    valor=valor,
                    per_ref=per_ref,
                )
            )


def _parse_s5002(evt, totalizador):
    """S-5002: IRRF por beneficiário.

    O evento traz o consolidado do beneficiário e, separadamente, o detalhe por
    demonstrativo de pagamento. Somar os dois contaria o imposto duas vezes, por
    isso o detalhe carrega ``per_ref`` e o consolidado não.
    """
    for elemento in evt.iter():
        if _nome(elemento) == "basesIrrf":
            continue
        if _nome(elemento) in ("infoIRRF", "idePgtoBenef"):
            per_ref = _texto(elemento, "perRef")
            if per_ref:
                _parse_cr_irrf(elemento, totalizador, per_ref=per_ref)
    for elemento in evt.iter():
        if _nome(elemento) in ("consolidApurMen", "consolidApurDia"):
            codigo = _texto(elemento, "CRMen") or _texto(elemento, "CRDia")
            grupo = "cr_men" if _nome(elemento) == "consolidApurMen" else "cr_dia"
            for nome, valor in _valores_do_grupo(elemento):
                totalizador.linhas.append(
                    LinhaTotalizador(
                        grupo=grupo,
                        codigo=codigo,
                        descricao=nome,
                        valor=valor,
                    )
                )


def _parse_evento(evt, tipo):
    totalizador = Totalizador(
        evento=tipo,
        id_evento=evt.get("Id"),
        per_apur=_texto(evt, "perApur"),
        ind_apuracao=_texto(evt, "indApuracao"),
        nr_rec_arq_base=_texto(evt, "nrRecArqBase"),
        cpf_trab=_texto(evt, "cpfTrab"),
        ind_exist_info=_texto(evt, "indExistInfo"),
        xml=etree.tostring(evt, encoding="unicode"),
    )
    if tipo == "S-5001":
        _parse_s5001(evt, totalizador)
    elif tipo == "S-5011":
        _parse_s5011(evt, totalizador)
    elif tipo == "S-5012":
        _parse_cr_irrf(evt, totalizador)
    elif tipo == "S-5002":
        _parse_s5002(evt, totalizador)
    # S-5003 e S-5013 (FGTS) são persistidos como cabeçalho: a conferência
    # atual não usa os valores de FGTS, e inventar grupos que ninguém lê seria
    # dívida sem uso.
    return totalizador


def parse_totalizadores(retorno_xml):
    """Lê os eventos totalizadores de um retorno do eSocial.

    Args:
        retorno_xml: XML do retorno do evento (str ou bytes).

    Returns:
        Lista de ``Totalizador``. Lista vazia quando o retorno não traz
        totalizador ou não é XML legível: retorno ilegível não pode derrubar o
        registro do aceite, que é o que o recibo prova.
    """
    if not retorno_xml:
        return []
    try:
        root = etree.fromstring(
            retorno_xml.encode("utf-8") if isinstance(retorno_xml, str) else retorno_xml
        )
    except (etree.XMLSyntaxError, ValueError):
        _logger.warning("eSocial: retorno ilegível ao procurar eventos totalizadores.")
        return []
    totalizadores = []
    for elemento in root.iter():
        tipo = EVENTOS_TOTALIZADORES.get(_nome(elemento))
        if tipo:
            totalizadores.append(_parse_evento(elemento, tipo))
    return totalizadores
