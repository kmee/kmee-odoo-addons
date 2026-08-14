# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Domínios dos eventos de SST do eSocial (leiaute S-1.3).

Os valores abaixo foram extraídos dos bindings da ``esociallib``, que são
gerados a partir dos XSD oficiais do leiaute. Nunca redigitar de memória: o
domínio errado só aparece na rejeição do evento, depois do prazo legal.

Estes domínios são compartilhados pelos módulos de EPI, ASO, CAT e pelos
intermediários do eSocial, e por isso moram no módulo base.
"""

# evtExpRisco/infoAmb/localAmb
LOCAL_AMBIENTE = [
    ("1", "1 - Estabelecimento do próprio empregador"),
    ("2", "2 - Estabelecimento de terceiros"),
]

# Tipo de inscrição do estabelecimento (mesmo domínio do S-1005).
TP_INSC_ESTABELECIMENTO = [
    ("1", "1 - CNPJ"),
    ("3", "3 - CAEPF"),
    ("4", "4 - CNO"),
]

# evtExpRisco/agNoc/tpAval
TIPO_AVALIACAO = [
    ("1", "1 - Critério quantitativo"),
    ("2", "2 - Critério qualitativo"),
]

# evtExpRisco/agNoc/unMed
UNIDADE_MEDIDA = [
    ("1", "1 - Dose diária de ruído"),
    ("2", "2 - Decibel linear (dB linear)"),
    ("3", "3 - Decibel C (dB(C))"),
    ("4", "4 - Decibel A (dB(A))"),
    ("5", "5 - Metro por segundo ao quadrado (m/s2)"),
    ("6", "6 - Metro por segundo elevado a 1,75 (m/s1,75)"),
    ("7", "7 - Parte por milhão (ppm)"),
    ("8", "8 - Miligrama por metro cúbico de ar (mg/m3)"),
    ("9", "9 - Fibra por centímetro cúbico (f/cm3)"),
    ("10", "10 - Grau Celsius (C)"),
    ("11", "11 - Metro por segundo (m/s)"),
    ("12", "12 - Porcentual"),
    ("13", "13 - Lux (lx)"),
    ("14", "14 - Unidade formadora de colônias por metro cúbico (ufc/m3)"),
    ("15", "15 - Dose diária"),
    ("16", "16 - Dose mensal"),
    ("17", "17 - Dose trimestral"),
    ("18", "18 - Dose anual"),
    ("19", "19 - Watt por metro quadrado (W/m2)"),
    ("20", "20 - Ampère por metro (A/m)"),
    ("21", "21 - Militesla (mT)"),
    ("22", "22 - Microtesla (uT)"),
    ("23", "23 - Miliampère (mA)"),
    ("24", "24 - Quilovolt por metro (kV/m)"),
    ("25", "25 - Volt por metro (V/m)"),
    ("26", "26 - Joule por metro quadrado (J/m2)"),
    ("27", "27 - Milijoule por centímetro quadrado (mJ/cm2)"),
    ("28", "28 - Milisievert (mSv)"),
    ("29", "29 - Milhão de partículas por decímetro cúbico (mppdc)"),
    ("30", "30 - Umidade relativa do ar (UR %)"),
]

# evtExpRisco/agNoc/epcEpi/utilizEPC
UTILIZACAO_EPC = [
    ("0", "0 - Não se aplica"),
    ("1", "1 - Não implementa"),
    ("2", "2 - Implementa"),
]

# evtExpRisco/agNoc/epcEpi/utilizEPI
UTILIZACAO_EPI = [
    ("0", "0 - Não se aplica"),
    ("1", "1 - Não utilizado"),
    ("2", "2 - Utilizado"),
]

# Indicadores S/N do leiaute (eficEpc, eficEpi, medProtecao, ...).
SIM_NAO = [
    ("S", "Sim"),
    ("N", "Não"),
]

# evtExpRisco/respReg/ideOC
IDE_ORGAO_CLASSE_RESP = [
    ("1", "1 - CRM"),
    ("4", "4 - CREA"),
    ("9", "9 - Outros"),
]

# evtCat/emitente/ideOC
IDE_ORGAO_CLASSE_EMITENTE = [
    ("1", "1 - CRM"),
    ("2", "2 - CRO"),
    ("3", "3 - RMS"),
]

# Código de ausência de agente nocivo (Tabela 22). Quem não tem exposição
# informa este código no S-2240, e não a omissão do grupo agNoc.
COD_AGENTE_NOCIVO_AUSENCIA = "09.01.001"

# Graus de insalubridade da NR-15 e os percentuais do art. 192 da CLT.
GRAU_INSALUBRIDADE = [
    ("minimo", "Mínimo (10%)"),
    ("medio", "Médio (20%)"),
    ("maximo", "Máximo (40%)"),
]

PERCENTUAL_INSALUBRIDADE = {
    "minimo": 10.0,
    "medio": 20.0,
    "maximo": 40.0,
}
