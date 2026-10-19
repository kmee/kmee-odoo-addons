# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Escopo atestado do PTRP e cálculo do seu resumo digital.

O Atestado Técnico do art. 89 da Portaria MTP 671/2021 declara que um programa
atende aos requisitos da norma. Para que essa declaração seja verificável, é
preciso responder duas perguntas:

1. **o que exatamente foi atestado?** Não é "o repositório": é o conjunto de
   código que implementa os requisitos declarados (leiaute do AFD e do AEJ,
   motor de apuração, imutabilidade da marcação, espelho de ponto). Corrigir
   um rótulo de tela, uma tradução ou um teste não altera a conformidade e
   não pode obrigar a reemitir documento nenhum.
2. **o que está rodando é aquilo?** Um resumo digital do escopo responde por
   parte disso; a outra parte é saber se algum módulo instalado sobrepõe os
   métodos do PTRP em tempo de execução, porque no Odoo dá para mudar o
   resultado sem tocar em uma linha deste código.

Daí a separação abaixo entre NUCLEO_ATESTADO (muda o que foi declarado) e o
resto (não muda). A lista é declarativa e versionada junto ao código de
propósito: um terceiro precisa conseguir reproduzir o mesmo resumo digital
sem depender de nós.
"""

import hashlib
import os
from fnmatch import fnmatch

# Arquivos que implementam os requisitos declarados no Atestado Técnico.
# Mudança aqui exige revisão do atestado; mudança fora daqui, não.
NUCLEO_ATESTADO = {
    "l10n_br_hr_attendance": (
        "models/l10n_br_hr_marcacao.py",  # imutabilidade (art. 74, IV e art. 82)
        "models/l10n_br_hr_rep.py",  # NSR sem lacunas (Anexo V)
        "models/hr_employee.py",  # conciliação do trabalhador
    ),
    "l10n_br_hr_attendance_afd": (
        "models/afd_layout.py",  # leiaute do Anexo V
        "models/afd_parser.py",
        "models/afd_crc.py",  # CRC-16 do item 8 do Anexo V
        "models/l10n_br_hr_afd_import.py",
        "models/l10n_br_hr_rep.py",
    ),
    "l10n_br_hr_attendance_apuracao": (
        "models/regras_jornada.py",  # regras materiais da CLT
        "models/l10n_br_hr_apuracao_dia.py",
        "models/l10n_br_hr_apuracao_periodo.py",
        "models/l10n_br_hr_ocorrencia.py",
        "data/l10n_br_hr_ocorrencia_data.xml",  # códigos do registro 07
    ),
    "l10n_br_hr_attendance_aej": (
        "models/aej_layout.py",  # leiaute do Anexo VI
        "models/l10n_br_hr_apuracao_periodo.py",
        "report/espelho_ponto.xml",  # espelho do art. 84
    ),
}

# Modelos cujo comportamento o atestado cobre. Sobreposição por módulo de
# terceiro descaracteriza o programa atestado mesmo sem alterar arquivo algum.
MODELOS_ATESTADOS = (
    "l10n_br.hr.marcacao",
    "l10n_br.hr.rep",
    "l10n_br.hr.apuracao.dia",
    "l10n_br.hr.apuracao.periodo",
    "l10n_br.hr.afd.import",
)

# Módulos autorizados a definir ou estender os modelos acima.
MODULOS_DO_PTRP = tuple(NUCLEO_ATESTADO) + ("l10n_br_hr_attendance_integridade",)


def marca_de_ausencia(nome_modulo):
    """Entrada de manifesto para módulo do escopo que não está instalado."""
    return "%s/(modulo nao instalado)" % nome_modulo


def _sha256_do_arquivo(caminho):
    """Resumo do arquivo com quebra de linha normalizada.

    A normalização evita que o mesmo conteúdo produza resumos diferentes só
    porque foi clonado em outro sistema operacional.
    """
    with open(caminho, "rb") as arquivo:
        conteudo = arquivo.read()
    return hashlib.sha256(conteudo.replace(b"\r\n", b"\n")).hexdigest()


def manifesto_do_modulo(caminho_modulo, nome_modulo, padroes):
    """Resumo de cada arquivo do escopo, na ordem do caminho relativo.

    Returns:
        Lista de ``(caminho_relativo, sha256)``. Arquivo declarado no escopo
        e ausente no disco entra com resumo vazio, porque some-lo em silêncio
        esconderia exatamente a alteração que se quer detectar.
    """
    entradas = []
    for padrao in sorted(padroes):
        encontrados = []
        for raiz, _dirs, arquivos in os.walk(caminho_modulo):
            for arquivo in arquivos:
                completo = os.path.join(raiz, arquivo)
                relativo = os.path.relpath(completo, caminho_modulo)
                if fnmatch(relativo.replace(os.sep, "/"), padrao):
                    encontrados.append((relativo.replace(os.sep, "/"), completo))
        if not encontrados:
            entradas.append(("%s/%s" % (nome_modulo, padrao), ""))
            continue
        for relativo, completo in sorted(encontrados):
            entradas.append(
                ("%s/%s" % (nome_modulo, relativo), _sha256_do_arquivo(completo))
            )
    return entradas


def resumo_do_manifesto(entradas):
    """Resumo digital único do escopo, a partir do manifesto ordenado.

    O texto canônico é ``caminho:resumo`` por linha, em ordem alfabética de
    caminho. Simples de reproduzir em qualquer linguagem, que é o requisito
    de quem precisa conferir sem confiar na nossa implementação.
    """
    canonico = "\n".join(
        "%s:%s" % (caminho, resumo) for caminho, resumo in sorted(entradas)
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
