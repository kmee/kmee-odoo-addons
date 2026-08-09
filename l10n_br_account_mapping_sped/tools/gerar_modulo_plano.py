#!/usr/bin/env python3
# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Gera um modulo Odoo de dados a partir da tabela dinamica oficial da RFB.

Uso:
    python3 gerar_modulo_plano.py TABELAS.xlsx L100A,L300A 1 \
        "PJ em Geral - Lucro Real" l10n_br_account_mapping_sped_plano1 \
        --leiaute 12 --saida /caminho/do/repo

A planilha e o pacote "Tabelas Dinamicas e Planos de Contas Referenciais"
publicado em http://sped.rfb.gov.br (ECF). Cada aba de plano referencial tem as
colunas: CODIGO, DESCRICAO, DT_INI, DT_FIM, TIPO (S/A), CONTA SUPERIOR, NIVEL,
NATUREZA.

Cada LEIAUTE vive no proprio subdiretorio (``data/l12/``) com o proprio
registro de plano (``plan_referencial_1_l12``) e IDs externos proprios
(``ref_1_l12_...``): regerar com o leiaute novo ACRESCENTA arquivos sem tocar
nos do leiaute anterior, entao a escrituracao retificadora de um ano antigo
continua achando a tabela da epoca, e o ``-u`` nao apaga o mapeamento que o
cliente fez sobre o leiaute anterior. Ao gerar por cima de um modulo
existente, as entradas de dados dos leiautes anteriores sao preservadas no
manifest.

O NIVEL vem da coluna oficial quando presente; sem ela, e calculado pela
cadeia de CONTA SUPERIOR (que nem sempre e prefixo do codigo: no plano 1 do
leiaute 12, a conta 3.11.01.05.01.48 tem pai 3.01.01.05.01).
"""

import argparse
import csv
import io
import os
import re
import sys

MANIFEST_TEMPLATE = """{header}
{{
    "name": "Plano Referencial RFB {plan_code} - {plan_name}",
    "summary": "Tabela oficial do plano referencial {plan_code} da RFB "
    "({abas_str}) para o registro I051 da ECD",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["l10n_br_account_mapping_sped"],
    "data": [
{data_entries}
    ],
    "installable": True,
}}
"""

PLAN_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<!--
    Copyright (C) 2026 KMEE Informatica LTDA
    License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

    Gerado por tools/gerar_modulo_plano.py a partir da tabela dinamica oficial
    da RFB (leiaute {leiaute}). Nao editar a mao: regerar com a planilha nova.
    Sem noupdate: a atualizacao da tabela chega pelo -u do modulo.
-->
<odoo>

    <record id="{plan_xmlid}" model="l10n_br_account_mapping.plan">
{name_field}
        <field name="sped_referential" eval="True" />
        <field name="sped_plan_code">{plan_code}</field>
        <field name="sped_layout_version">{leiaute}</field>
        <field name="company_id" eval="False" />
    </record>

</odoo>
"""


def _clean(text):
    return " ".join(str(text or "").split())


def _date_iso(value):
    """DT no formato ddmmaaaa (ou datetime do openpyxl) para ISO."""
    if value is None or value == "":
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    digits = "".join(c for c in str(value) if c.isdigit())
    if len(digits) == 8:
        return f"{digits[4:]}-{digits[2:4]}-{digits[:2]}"
    return ""


def _xmlid(plan_ref, leiaute, code):
    safe = code.replace(".", "_").replace("-", "_")
    return f"ref_{plan_ref}_l{leiaute}_{safe}"


def _nivel_pela_cadeia(contas):
    """NIVEL calculado pela cadeia de pais quando a planilha nao o traz."""
    parent_by_code = {c["code"]: c["parent"] for c in contas}
    level_by_code = {}

    def level(code, seen=()):
        if code in level_by_code:
            return level_by_code[code]
        parent = parent_by_code.get(code, "")
        if not parent or parent == code or code in seen:
            lv = 1
        else:
            lv = level(parent, seen + (code,)) + 1
        level_by_code[code] = lv
        return lv

    for c in contas:
        c["level"] = level(c["code"])
    return contas


def ler_abas(xlsx_path, abas):
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    contas = []
    for aba in abas:
        ws = wb[aba]
        rows = ws.iter_rows(values_only=True)
        header = next(rows)
        idx = {(_clean(h) or f"col{i}").upper(): i for i, h in enumerate(header)}

        def col(row, *names):
            for name in names:
                if name in idx and idx[name] < len(row):
                    return row[idx[name]]
            return None

        for row in rows:
            code = _clean(col(row, "CÓDIGO", "CODIGO"))
            if not code:
                continue
            nivel = _clean(col(row, "NÍVEL", "NIVEL"))
            contas.append(
                {
                    "code": code,
                    "name": _clean(col(row, "DESCRIÇÃO", "DESCRICAO")),
                    "date_start": _date_iso(col(row, "DT_INI")),
                    "date_end": _date_iso(col(row, "DT_FIM")),
                    "type": _clean(col(row, "TIPO")) or "A",
                    "parent": _clean(col(row, "CONTA SUPERIOR")),
                    "nature": _clean(col(row, "NATUREZA")),
                    "level": int(nivel) if nivel.isdigit() else None,
                    "aba": aba,
                }
            )
    if any(c["level"] is None for c in contas):
        contas = _nivel_pela_cadeia(contas)
    return contas


def _data_entries_existentes(base, leiaute):
    """Entradas de dados de OUTROS leiautes ja presentes no modulo."""
    manifest = os.path.join(base, "__manifest__.py")
    if not os.path.exists(manifest):
        return []
    with open(manifest, encoding="utf-8") as f:
        content = f.read()
    entries = re.findall(r'"(data/[^"]+)"', content)
    return [e for e in entries if f"_l{leiaute}." not in e and f"/l{leiaute}/" not in e]


def gerar_modulo(contas, plan_code, plan_name, module, leiaute, saida):
    base = os.path.join(saida, module)
    data_dir = os.path.join(base, "data", f"l{leiaute}")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(base, "readme"), exist_ok=True)

    anteriores = _data_entries_existentes(base, leiaute)
    plan_xmlid = f"plan_referencial_{plan_code}_l{leiaute}"
    header = (
        "# Copyright (C) 2026 KMEE Informatica LTDA\n"
        "# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).\n"
    )

    abas = sorted({c["aba"] for c in contas})
    abas_str = ", ".join(abas)
    novas = [
        f"data/mapping_plan_l{leiaute}.xml",
        f"data/l{leiaute}/l10n_br_account_mapping.account.csv",
    ]
    entries = anteriores + novas
    # concatenacao em vez de f-string: o flake8 do repo tokeniza o interior
    # de f-strings e acusa E231 falso na virgula do literal
    data_entries = "\n".join('        "' + e + '",' for e in entries)
    with open(os.path.join(base, "__manifest__.py"), "w", encoding="utf-8") as f:
        f.write(
            MANIFEST_TEMPLATE.format(
                header=header,
                plan_code=plan_code,
                plan_name=plan_name,
                abas_str=abas_str,
                data_entries=data_entries,
            )
        )
    with open(os.path.join(base, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(header)

    with open(
        os.path.join(base, "data", f"mapping_plan_l{leiaute}.xml"),
        "w",
        encoding="utf-8",
    ) as f:
        # replica a regra de 88 colunas do prettier do repo: inline quando
        # cabe, quebrado quando nao; assim regenerar = identico ao formatado
        full_name = (
            f"Plano Referencial RFB {plan_code} - {plan_name} (leiaute {leiaute})"
        )
        # literais com espacos fora de f-string: o flake8 do repo tokeniza o
        # interior de f-strings e acusa E221 falso nos espacos de indentacao
        inline = '        <field name="name">' + full_name + "</field>"
        if len(inline) <= 88:
            name_field = inline
        else:
            name_field = (
                "        <field\n"
                '            name="name"\n'
                "        >" + full_name + "</field>"
            )
        f.write(
            PLAN_XML_TEMPLATE.format(
                leiaute=leiaute,
                plan_xmlid=plan_xmlid,
                plan_code=plan_code,
                plan_name=plan_name,
                name_field=name_field,
            )
        )

    buf = io.StringIO()
    # \n explicito: o csv.writer usa \r\n por padrao, e o pre-commit do
    # repo normaliza para \n; sem isso, toda regeracao sujaria o diff
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "id",
            "plan_id/id",
            "code",
            "name",
            "sped_account_type",
            "sped_parent_code",
            "sped_nature",
            "sped_level",
            "date_start",
            "date_end",
        ]
    )
    vistos = set()
    for c in contas:
        xmlid = _xmlid(plan_code, leiaute, c["code"])
        if xmlid in vistos:
            print(  # noqa: T201 pylint: disable=print-used
                f"  AVISO: codigo duplicado ignorado: {c['code']}"
            )
            continue
        vistos.add(xmlid)
        writer.writerow(
            [
                xmlid,
                f"{module}.{plan_xmlid}",
                c["code"],
                c["name"],
                c["type"],
                c["parent"],
                c["nature"],
                c["level"],
                c["date_start"],
                c["date_end"],
            ]
        )
    with open(
        os.path.join(data_dir, "l10n_br_account_mapping.account.csv"),
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        f.write(buf.getvalue())

    with open(
        os.path.join(base, "readme", "DESCRIPTION.rst"), "w", encoding="utf-8"
    ) as f:
        f.write(
            f"Carga oficial do **plano referencial {plan_code} da RFB**\n"
            f"({plan_name}), abas {abas_str} do pacote de tabelas\n"
            "dinamicas do SPED.\n\n"
            f"Sao {len(vistos)} contas referenciais, com tipo\n"
            "(sintetica/analitica), hierarquia, nivel, natureza e vigencia.\n"
            "Cada leiaute da RFB vive no proprio subdiretorio de dados e no\n"
            "proprio registro de plano: os leiautes convivem, e a\n"
            "escrituracao retificadora de um ano antigo usa a tabela da\n"
            "epoca. O modulo e gerado por ``tools/gerar_modulo_plano.py`` a\n"
            "partir da planilha publicada em http://sped.rfb.gov.br.\n\n"
            "Depois de instalar, vincule as contas do Odoo as contas\n"
            "referenciais (analiticas) e aponte o plano na empresa: e o que\n"
            "alimenta o registro I051 da ECD.\n"
        )
    with open(
        os.path.join(base, "readme", "CONTRIBUTORS.rst"), "w", encoding="utf-8"
    ) as f:
        f.write("* Luis Felipe Mileo <mileo@kmee.com.br>\n")
    return len(vistos)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xlsx")
    ap.add_argument("abas", help="abas separadas por virgula, ex.: L100A,L300A")
    ap.add_argument("plan_code", help="COD_PLAN_REF, ex.: 1")
    ap.add_argument("plan_name")
    ap.add_argument("module")
    ap.add_argument("--leiaute", required=True)
    ap.add_argument("--saida", default=".")
    args = ap.parse_args()

    contas = ler_abas(args.xlsx, args.abas.split(","))
    total = gerar_modulo(
        contas,
        args.plan_code,
        args.plan_name,
        args.module,
        args.leiaute,
        args.saida,
    )
    print(  # noqa: T201 pylint: disable=print-used
        f"{args.module}: {total} contas geradas"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
