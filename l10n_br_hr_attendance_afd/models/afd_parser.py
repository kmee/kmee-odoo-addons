# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Leitura e escrita do AFD, sem ORM.

O parser é deliberadamente tolerante quanto ao que NÃO compromete o dado
fiscal (espaços sobrando, CRLF ausente na última linha, hexadecimal em
minúsculas) e rigoroso quanto ao que compromete: CRC divergente, data
inválida, NSR fora de ordem. Divergência não interrompe a leitura - vira
ocorrência no resultado, para que o operador veja o arquivo inteiro de uma vez
em vez de descobrir um problema por execução.
"""

import re
from datetime import datetime, timedelta, timezone

from . import afd_layout
from .afd_crc import crc_confere, crc_da_linha

RE_DATA_HORA = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-])(\d{2})(\d{2})$"
)


class ErroAfd(Exception):
    """Erro que impede interpretar o arquivo como AFD."""


class Ocorrencia:
    """Problema encontrado em uma linha, sem interromper a leitura."""

    def __init__(self, numero_linha, codigo, mensagem, conteudo=""):
        self.numero_linha = numero_linha
        self.codigo = codigo
        self.mensagem = mensagem
        self.conteudo = conteudo

    def __repr__(self):
        return "<Ocorrencia linha=%s %s: %s>" % (
            self.numero_linha,
            self.codigo,
            self.mensagem,
        )


class ResultadoAfd:
    """O que a leitura de um arquivo produziu."""

    def __init__(self, leiaute):
        self.leiaute = leiaute
        self.cabecalho = {}
        self.trailer = {}
        self.marcacoes = []
        self.eventos = []
        self.ocorrencias = []
        self.lacunas_nsr = []
        self.assinatura = ""

    @property
    def tem_erro(self):
        return any(o.codigo != "aviso" for o in self.ocorrencias)

    def adiciona_ocorrencia(self, numero_linha, codigo, mensagem, conteudo=""):
        self.ocorrencias.append(Ocorrencia(numero_linha, codigo, mensagem, conteudo))


def _para_datetime_utc(texto):
    """Converte ``AAAA-MM-ddThh:mm:00ZZZZZ`` em datetime naive em UTC.

    O fuso é obrigatório no leiaute justamente porque o horário de verão já
    fez marcações mudarem de hora ao serem reinterpretadas; guardamos em UTC e
    reconvertimos na exibição.
    """
    casamento = RE_DATA_HORA.match(texto.strip())
    if not casamento:
        raise ValueError("Data/hora fora do formato do Anexo V: %r" % texto)
    ano, mes, dia, hora, minuto, segundo, sinal, tz_h, tz_m = casamento.groups()
    deslocamento = timedelta(hours=int(tz_h), minutes=int(tz_m))
    if sinal == "-":
        deslocamento = -deslocamento
    momento = datetime(
        int(ano),
        int(mes),
        int(dia),
        int(hora),
        int(minuto),
        int(segundo),
        tzinfo=timezone(deslocamento),
    )
    return momento.astimezone(timezone.utc).replace(tzinfo=None)


def _para_datetime_1510(data, hora, fuso_horas=-3):
    """Converte ``ddmmaaaa`` + ``hhmm`` do leiaute antigo em UTC naive.

    A Portaria 1.510/2009 não gravava fuso: o relógio marcava a hora local. Sem
    essa informação no arquivo, o fuso do estabelecimento é um parâmetro da
    importação - assumir UTC deslocaria toda a jornada em três horas.
    """
    momento = datetime.strptime(data + hora, "%d%m%Y%H%M")
    return momento - timedelta(hours=fuso_horas)


def formata_datetime(momento, fuso_horas=-3):
    """Formata datetime naive em UTC no padrão ``DH`` do Anexo V."""
    local = momento + timedelta(hours=fuso_horas)
    sinal = "-" if fuso_horas < 0 else "+"
    return "%s%s%02d%02d" % (
        local.strftime("%Y-%m-%dT%H:%M:00"),
        sinal,
        abs(int(fuso_horas)),
        int(abs(fuso_horas) % 1 * 60),
    )


def detecta_leiaute(conteudo):
    """Descobre se o arquivo é da Portaria 671 ou da 1.510.

    O cabeçalho da 671 tem 302 caracteres e traz a versão "003" nas posições
    251-253; o da 1.510 tem 232 e data no formato ``ddmmaaaa``. Usamos o
    tamanho da primeira linha, que é o discriminador mais estável.
    """
    primeira = conteudo.split("\r\n")[0].split("\n")[0]
    if len(primeira) >= 253 and primeira[250:253] == afd_layout.VERSAO_LEIAUTE_671:
        return "671"
    tamanho_671 = afd_layout.tamanho_registro("671", "1")
    return "671" if len(primeira) >= tamanho_671 else "1510"


def ler_afd(conteudo, leiaute=None, fuso_horas=-3):
    """Interpreta o conteúdo de um AFD.

    Args:
        conteudo: texto do arquivo (já decodificado de ISO-8859-1).
        leiaute: ``"671"``, ``"1510"`` ou ``None`` para detectar.
        fuso_horas: fuso do estabelecimento, usado apenas no leiaute 1.510.

    Returns:
        ``ResultadoAfd`` com cabeçalho, marcações, eventos e ocorrências.
    """
    leiaute = leiaute or detecta_leiaute(conteudo)
    resultado = ResultadoAfd(leiaute)
    linhas = conteudo.replace("\r\n", "\n").split("\n")
    nsrs_vistos = []

    for indice, linha in enumerate(linhas, start=1):
        if not linha.strip():
            continue
        if linha.startswith(afd_layout.ASSINATURA_EM_ARQUIVO):
            resultado.assinatura = linha.strip()
            continue
        tipo = afd_layout.identifica_tipo(linha)
        if tipo not in afd_layout.LEIAUTES[leiaute]:
            resultado.adiciona_ocorrencia(
                indice,
                "tipo_desconhecido",
                "Tipo de registro %r não previsto no leiaute %s." % (tipo, leiaute),
                linha[:60],
            )
            continue

        esperado = afd_layout.tamanho_registro(leiaute, tipo)
        if len(linha) < esperado:
            resultado.adiciona_ocorrencia(
                indice,
                "tamanho",
                "Registro tipo %s com %d caracteres; o leiaute exige %d."
                % (tipo, len(linha), esperado),
                linha[:60],
            )
            continue

        if leiaute == "671" and tipo in afd_layout.TIPOS_COM_CRC:
            linha_crc = linha[:esperado]
            if not crc_confere(linha_crc):
                resultado.adiciona_ocorrencia(
                    indice,
                    "crc",
                    "CRC-16 divergente no registro tipo %s: arquivo traz %r, "
                    "o cálculo dá %r."
                    % (tipo, linha_crc[-4:], crc_da_linha(linha_crc)),
                    linha[:60],
                )

        try:
            _interpreta_linha(resultado, leiaute, tipo, linha, indice, fuso_horas)
        except ValueError as erro:
            resultado.adiciona_ocorrencia(indice, "conteudo", str(erro), linha[:60])
            continue

        if tipo != "9":
            campo_nsr = afd_layout.fatia(linha, leiaute, tipo, "nsr")
            if campo_nsr.isdigit() and tipo != "1":
                nsrs_vistos.append(int(campo_nsr))

    resultado.lacunas_nsr = _detecta_lacunas(sorted(set(nsrs_vistos)))
    _confere_trailer(resultado)
    return resultado


def _interpreta_linha(resultado, leiaute, tipo, linha, indice, fuso_horas):
    """Traduz uma linha para dicionário, conforme o tipo de registro."""
    campo = lambda nome: afd_layout.fatia(linha, leiaute, tipo, nome)  # noqa: E731

    if tipo == "1":
        resultado.cabecalho = {
            "tipo_identificador_empregador": campo("tipo_identificador_empregador"),
            "cnpj_cpf_empregador": campo("cnpj_cpf_empregador"),
            "razao_social": campo("razao_social"),
        }
        if leiaute == "671":
            resultado.cabecalho.update(
                {
                    "identificador_rep": campo("identificador_rep"),
                    "data_inicial": campo("data_inicial"),
                    "data_final": campo("data_final"),
                    "versao_leiaute": campo("versao_leiaute"),
                    "modelo": campo("modelo"),
                }
            )
        else:
            resultado.cabecalho.update(
                {
                    "identificador_rep": campo("numero_fabricacao"),
                    "data_inicial": campo("data_inicial"),
                    "data_final": campo("data_final"),
                    "versao_leiaute": "1510",
                }
            )
        return

    if tipo == "9":
        chaves = [c.nome for c in afd_layout.LEIAUTES[leiaute]["9"]]
        resultado.trailer = {
            chave: int(campo(chave) or 0)
            for chave in chaves
            if chave.startswith("qtd_")
        }
        return

    if leiaute == "671" and tipo in afd_layout.TIPOS_MARCACAO_671:
        registro = {
            "nsr": int(campo("nsr")),
            "tipo_registro": tipo,
            "datetime_marcacao": _para_datetime_utc(campo("data_hora_marcacao")),
            "cpf": campo("cpf").lstrip("0"),
            "linha": indice,
        }
        if tipo == "7":
            registro.update(
                {
                    "datetime_gravacao": _para_datetime_utc(
                        campo("data_hora_gravacao")
                    ),
                    "coletor": campo("coletor"),
                    "offline": campo("offline") == "1",
                    "hash_registro": campo("hash"),
                }
            )
        resultado.marcacoes.append(registro)
        return

    if leiaute == "1510" and tipo in afd_layout.TIPOS_MARCACAO_1510:
        resultado.marcacoes.append(
            {
                "nsr": int(campo("nsr")),
                "tipo_registro": tipo,
                "datetime_marcacao": _para_datetime_1510(
                    campo("data_marcacao"), campo("hora_marcacao"), fuso_horas
                ),
                "pis": campo("pis").lstrip("0"),
                "linha": indice,
            }
        )
        return

    # Registros 2, 4, 5 e 6: eventos do REP. Não viram jornada, mas ficam
    # registrados porque o Auditor-Fiscal pode pedi-los (ajuste de relógio é
    # justamente o que se olha quando se suspeita de adulteração).
    resultado.eventos.append(
        {
            "nsr": int(campo("nsr")),
            "tipo_registro": tipo,
            "linha": indice,
            "conteudo": linha.rstrip(),
        }
    )


def _detecta_lacunas(nsrs):
    """Faixas de NSR ausentes na sequência lida (RP-08).

    Lacuna é indício de marcação suprimida - por isso vira alerta bloqueante
    no fechamento, não apenas um aviso na importação.
    """
    lacunas = []
    for anterior, seguinte in zip(nsrs, nsrs[1:]):
        if seguinte > anterior + 1:
            lacunas.append((anterior + 1, seguinte - 1))
    return lacunas


def _confere_trailer(resultado):
    """Compara as contagens declaradas no trailer com as lidas."""
    if not resultado.trailer:
        resultado.adiciona_ocorrencia(0, "trailer", "Arquivo sem registro trailer.")
        return
    lidos = {"qtd_tipo_3": 0, "qtd_tipo_7": 0}
    for marcacao in resultado.marcacoes:
        chave = "qtd_tipo_%s" % marcacao["tipo_registro"]
        lidos[chave] = lidos.get(chave, 0) + 1
    for chave, quantidade in lidos.items():
        declarado = resultado.trailer.get(chave)
        if declarado is not None and declarado != quantidade:
            resultado.adiciona_ocorrencia(
                0,
                "trailer",
                "Trailer declara %d registros %s, o arquivo tem %d."
                % (declarado, chave.replace("qtd_tipo_", "tipo "), quantidade),
            )


def gerar_afd(cabecalho, marcacoes, fuso_horas=-3, assinatura_em_arquivo=True):
    """Gera um AFD no leiaute 671 (usado pelo REP-P e pela reexportação).

    Args:
        cabecalho: dicionário com os campos do registro tipo 1.
        marcacoes: lista de dicionários com ``nsr``, ``datetime_marcacao``,
            ``cpf`` e, para o tipo 7, ``datetime_gravacao``, ``coletor``,
            ``offline`` e ``hash_registro``.
        fuso_horas: fuso gravado nos campos de data e hora.
        assinatura_em_arquivo: grava o literal do Anexo V indicando que a
            assinatura vai em ``.p7s`` destacado.

    Returns:
        Texto do arquivo, com CRLF, pronto para gravar em ISO-8859-1.
    """
    linhas = []
    contagem = {"3": 0, "7": 0, "2": 0, "4": 0, "5": 0, "6": 0}

    valores_cabecalho = dict(cabecalho)
    valores_cabecalho.setdefault("nsr", "0")
    valores_cabecalho["tipo_registro"] = "1"
    valores_cabecalho["versao_leiaute"] = afd_layout.VERSAO_LEIAUTE_671
    linha = afd_layout.monta_registro("671", "1", valores_cabecalho)
    linhas.append(linha[:-4] + crc_da_linha(linha))

    for marcacao in marcacoes:
        tipo = marcacao.get("tipo_registro", "3")
        contagem[tipo] = contagem.get(tipo, 0) + 1
        valores = {
            "nsr": marcacao["nsr"],
            "tipo_registro": tipo,
            "data_hora_marcacao": formata_datetime(
                marcacao["datetime_marcacao"], fuso_horas
            ),
            "cpf": marcacao.get("cpf", ""),
        }
        if tipo == "7":
            valores.update(
                {
                    "data_hora_gravacao": formata_datetime(
                        marcacao.get("datetime_gravacao")
                        or marcacao["datetime_marcacao"],
                        fuso_horas,
                    ),
                    "coletor": marcacao.get("coletor") or "02",
                    "offline": "1" if marcacao.get("offline") else "0",
                    "hash": marcacao.get("hash_registro", ""),
                }
            )
            linhas.append(afd_layout.monta_registro("671", "7", valores))
        else:
            linha = afd_layout.monta_registro("671", "3", valores)
            linhas.append(linha[:-4] + crc_da_linha(linha))

    trailer = {
        "nsr": "9" * 9,
        "qtd_tipo_2": contagem["2"],
        "qtd_tipo_3": contagem["3"],
        "qtd_tipo_4": contagem["4"],
        "qtd_tipo_5": contagem["5"],
        "qtd_tipo_6": contagem["6"],
        "qtd_tipo_7": contagem["7"],
        "tipo_registro": "9",
    }
    linhas.append(afd_layout.monta_registro("671", "9", trailer))

    if assinatura_em_arquivo:
        linhas.append(afd_layout.ASSINATURA_EM_ARQUIVO.ljust(100, " "))

    return afd_layout.TERMINADOR_LINHA.join(linhas) + afd_layout.TERMINADOR_LINHA


def nome_arquivo_afd(tipo_rep, identificador, cnpj_cpf):
    """Nome do AFD conforme o item 10 do Anexo V."""
    sufixo = {"rep_c": "REP_C", "rep_a": "REP_A", "rep_p": "REP_P"}[tipo_rep]
    if tipo_rep == "rep_a":
        return "AFD%s%s.txt" % (cnpj_cpf, sufixo)
    return "AFD%s%s%s.txt" % (identificador, cnpj_cpf, sufixo)
