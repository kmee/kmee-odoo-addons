# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Leiaute do AEJ - Arquivo Eletrônico de Jornada.

**Anexo VI da Portaria MTP 671/2021.** Diferente do AFD, que é posicional, o
AEJ é delimitado por ``|`` (pipe): cada linha é um registro e cada campo
termina em pipe, exceto o último.

Regras do anexo que o gerador respeita:

- texto ISO-8859-1, uma linha por registro, terminada em CRLF, sem linhas em
  branco;
- data ``AAAA-MM-dd``; hora ``hhmm``; data e hora ``AAAA-MM-ddThh:mm:00ZZZZZ``,
  com fuso obrigatório;
- ``durJornada`` em MINUTOS, já considerando a redução da hora noturna quando
  o horário for noturno.

O AEJ é gerado pelo PTRP (Programa de Tratamento de Registro de Ponto) - aqui,
o Odoo - a partir das marcações tratadas, e é ele que leva as correções que o
AFD, por ser imutável, não pode conter.
"""

from datetime import timedelta

ENCODING_AEJ = "iso-8859-1"
TERMINADOR_LINHA = "\r\n"
DELIMITADOR = "|"
VERSAO_LEIAUTE = "001"

# Campos de cada tipo de registro, na ordem do Anexo VI.
CAMPOS = {
    "01": (
        "tipoReg",
        "tpIdtEmpregador",
        "idtEmpregador",
        "caepf",
        "cno",
        "razaoOuNome",
        "dataInicialAej",
        "dataFinalAej",
        "dataHoraGerAej",
        "versaoAej",
    ),
    "02": ("tipoReg", "idRepAej", "tpRep", "nrRep"),
    "03": ("tipoReg", "idtVinculoAej", "cpf", "nomeEmp"),
    "04": (
        "tipoReg",
        "codHorContratual",
        "durJornada",
        "hrEntrada01",
        "hrSaida01",
        "hrEntrada02",
        "hrSaida02",
    ),
    "05": (
        "tipoReg",
        "idtVinculoAej",
        "dataHoraMarc",
        "idRepAej",
        "tpMarc",
        "seqEntSaida",
        "fonteMarc",
        "codHorContratual",
        "motivo",
    ),
    "06": ("tipoReg", "idtVinculoAej", "matEsocial"),
    "07": (
        "tipoReg",
        "idtVinculoAej",
        "tipoAusenOuComp",
        "data",
        "qtMinutos",
        "tipoMovBH",
    ),
    "08": (
        "tipoReg",
        "nomeProg",
        "versaoProg",
        "tpIdtDesenv",
        "idtDesenv",
        "razaoNomeDesenv",
        "emailDesenv",
    ),
    "99": (
        "tipoReg",
        "qtRegistrosTipo01",
        "qtRegistrosTipo02",
        "qtRegistrosTipo03",
        "qtRegistrosTipo04",
        "qtRegistrosTipo05",
        "qtRegistrosTipo06",
        "qtRegistrosTipo07",
        "qtRegistrosTipo08",
    ),
}

# Tipo do REP no registro 02 (campo tpRep).
TIPO_REP_AEJ = {"rep_c": "1", "rep_a": "2", "rep_p": "3"}

# Códigos do campo tipoAusenOuComp do registro 07.
AUSENCIA_DSR = "1"
AUSENCIA_FALTA = "2"
AUSENCIA_BANCO_HORAS = "3"
AUSENCIA_FOLGA_FERIADO = "4"

# Tipo de movimento no banco de horas (campo tipoMovBH).
BH_INCLUSAO = "1"
BH_COMPENSACAO = "2"


def monta_registro(tipo, valores):
    """Serializa um registro do AEJ com os campos delimitados por pipe.

    Campos ausentes viram vazio - o anexo prevê tamanho "0 a N" em vários
    deles, e vazio é a forma de dizer "não se aplica".
    """
    return DELIMITADOR.join(str(valores.get(campo, "") or "") for campo in CAMPOS[tipo])


def formata_data(data):
    """Formato ``D`` do Anexo VI: ``AAAA-MM-dd``."""
    return data.strftime("%Y-%m-%d") if data else ""


def formata_hora(hora_local):
    """Formato ``H`` do Anexo VI: ``hhmm``."""
    return hora_local.strftime("%H%M") if hora_local else ""


def formata_datetime(momento_utc, fuso_horas=-3):
    """Formato ``DH`` do Anexo VI, com fuso obrigatório.

    Recebe ``datetime`` naive em UTC (como o ORM guarda) e devolve o horário
    local com o deslocamento explícito - sem o fuso, a mesma marcação é lida
    de formas diferentes conforme quem abre o arquivo.
    """
    if not momento_utc:
        return ""
    local = momento_utc + timedelta(hours=fuso_horas)
    sinal = "-" if fuso_horas < 0 else "+"
    return "%s%s%02d%02d" % (
        local.strftime("%Y-%m-%dT%H:%M:00"),
        sinal,
        int(abs(fuso_horas)),
        int(abs(fuso_horas) % 1 * 60),
    )


def nome_arquivo_aej(cnpj_cpf, date_from, date_to):
    """Nome do arquivo entregue à fiscalização.

    A Portaria não fixa o nome do AEJ como fixa o do AFD; o padrão adotado
    identifica empregador e período, que é o que o Auditor-Fiscal precisa para
    conferir a competência pedida.
    """
    return "AEJ%s%s%s.txt" % (
        cnpj_cpf,
        date_from.strftime("%Y%m%d"),
        date_to.strftime("%Y%m%d"),
    )
