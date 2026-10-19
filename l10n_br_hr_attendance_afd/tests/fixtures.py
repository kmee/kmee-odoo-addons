# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Geradores de AFD para os testes.

Preferimos montar os arquivos aqui, com o mesmo leiaute que o parser lê, a
guardar binários opacos: quando o leiaute mudar, o teste acusa a mudança em
vez de comparar contra um arquivo que ninguém sabe mais de onde veio. Amostras
reais de fabricante entram como complemento, nunca como única cobertura.
"""

from datetime import datetime

from ..models import afd_layout, afd_parser
from ..models.afd_crc import crc_da_linha

CNPJ_EMPREGADOR = "12345678000195"
NUMERO_FABRICACAO = "12345678901234567"
CPF_EMPREGADO = "43461292850"
PIS_EMPREGADO = "12045678905"


def cabecalho_671(data_inicial="2026-03-01", data_final="2026-03-31"):
    return {
        "tipo_identificador_empregador": "1",
        "cnpj_cpf_empregador": CNPJ_EMPREGADOR,
        "cno_caepf": "",
        "razao_social": "KMEE INFORMATICA LTDA",
        "identificador_rep": NUMERO_FABRICACAO,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "data_hora_geracao": "2026-04-01T08:00:00-0300",
        "tipo_identificador_fabricante": "1",
        "cnpj_cpf_fabricante": CNPJ_EMPREGADOR,
        "modelo": "REP MODELO X",
    }


def marcacoes_671(dia=2, horas=(11, 15, 16, 20), nsr_inicial=1, cpf=CPF_EMPREGADO):
    """Marcações em UTC. 11h UTC = 08h em Brasília."""
    return [
        {
            "nsr": nsr_inicial + indice,
            "tipo_registro": "3",
            "datetime_marcacao": datetime(2026, 3, dia, hora, 0),
            "cpf": cpf,
        }
        for indice, hora in enumerate(horas)
    ]


def afd_671(marcacoes=None, **kwargs):
    return afd_parser.gerar_afd(cabecalho_671(**kwargs), marcacoes or marcacoes_671())


def afd_671_com_lacuna():
    """NSRs 1, 2 e 5: faltam o 3 e o 4."""
    marcacoes = marcacoes_671(horas=(11, 15), nsr_inicial=1)
    marcacoes += marcacoes_671(horas=(20,), nsr_inicial=5)
    return afd_parser.gerar_afd(cabecalho_671(), marcacoes)


def afd_671_com_crc_invalido():
    """Troca o CRC de uma marcação para simular adulteração."""
    conteudo = afd_671()
    linhas = conteudo.split(afd_layout.TERMINADOR_LINHA)
    linhas[1] = linhas[1][:-4] + "FFFF"
    return afd_layout.TERMINADOR_LINHA.join(linhas)


def afd_1510(pis=PIS_EMPREGADO):
    """Arquivo no leiaute da Portaria 1.510/2009 (sem CRC, com PIS).

    Continua legal para REP-C certificado antes de 10/02/2022 (art. 96), e é a
    base instalada da maioria dos clientes.
    """
    linhas = []
    linhas.append(
        afd_layout.monta_registro(
            "1510",
            "1",
            {
                "nsr": "0",
                "tipo_registro": "1",
                "tipo_identificador_empregador": "1",
                "cnpj_cpf_empregador": CNPJ_EMPREGADOR,
                "cei": "",
                "razao_social": "KMEE INFORMATICA LTDA",
                "numero_fabricacao": NUMERO_FABRICACAO,
                "data_inicial": "01032026",
                "data_final": "31032026",
                "data_geracao": "01042026",
                "hora_geracao": "0800",
            },
        )
    )
    for indice, hora in enumerate(("0800", "1200", "1300", "1700")):
        linhas.append(
            afd_layout.monta_registro(
                "1510",
                "3",
                {
                    "nsr": indice + 1,
                    "tipo_registro": "3",
                    "data_marcacao": "02032026",
                    "hora_marcacao": hora,
                    "pis": pis,
                },
            )
        )
    linhas.append(
        afd_layout.monta_registro(
            "1510",
            "9",
            {
                "nsr": "9" * 9,
                "qtd_tipo_2": 0,
                "qtd_tipo_3": 4,
                "qtd_tipo_4": 0,
                "qtd_tipo_5": 0,
                "tipo_registro": "9",
            },
        )
    )
    return afd_layout.TERMINADOR_LINHA.join(linhas) + afd_layout.TERMINADOR_LINHA


def linha_com_crc(leiaute, tipo, valores):
    """Monta uma linha isolada já com o CRC calculado."""
    linha = afd_layout.monta_registro(leiaute, tipo, valores)
    return linha[:-4] + crc_da_linha(linha)
