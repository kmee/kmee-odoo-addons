# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Constantes para geração de arquivos do governo brasileiro (SEFIP, DIRF, CAGED)."""

MESES = [
    ("1", "Janeiro"),
    ("2", "Fevereiro"),
    ("3", "Março"),
    ("4", "Abril"),
    ("5", "Maio"),
    ("6", "Junho"),
    ("7", "Julho"),
    ("8", "Agosto"),
    ("9", "Setembro"),
    ("10", "Outubro"),
    ("11", "Novembro"),
    ("12", "Dezembro"),
    ("13", "13º Salário"),
]

CATEGORIA_TRABALHADOR = [
    ("101", "Empregado - Geral"),
    ("102", "Empregado - Trabalhador Rural por Prazo Determinado"),
    ("103", "Empregado - Aprendiz"),
    ("104", "Empregado - Doméstico"),
    ("105", "Empregado - Contrato a Termo (Lei 9.601/98)"),
    ("106", "Trabalhador Temporário (Lei 6.019/74)"),
    ("111", "Empregado - Contrato Intermitente"),
    ("301", "Servidor Público - Titular de Cargo Efetivo"),
    ("302", "Servidor Público - Ocupante de Cargo Exclusivo em Comissão"),
    ("303", "Agente Político"),
    ("305", "Servidor Público (Regime Estatutário - RPPS)"),
    ("306", "Servidor Público (Regime Estatutário - RGPS)"),
    ("309", "Agente Público - Outros"),
    ("401", "Dirigente Sindical - Segurado Especial"),
    ("410", "Trabalhador Cedido"),
    ("701", "Contribuinte Individual - Autônomo Geral"),
    ("721", "Contribuinte Individual - Diretor sem FGTS"),
    ("722", "Contribuinte Individual - Diretor com FGTS"),
    ("723", "Contribuinte Individual - Empresário/Sócio"),
    ("731", "Contribuinte Individual - Cooperado"),
    ("734", "Contribuinte Individual - Transportador Cooperado"),
    ("738", "Contribuinte Individual - Cooperado Filiado a Cooperativa"),
    ("741", "Contribuinte Individual - Microempreendedor Individual"),
    ("751", "Contribuinte Individual - Magistrado Classista Temporário da JT"),
    ("761", "Contribuinte Individual - Associado Eleito para Direção"),
    ("771", "Contribuinte Individual - Membro do Conselho Tutelar"),
    ("781", "Ministro de Confissão Religiosa / Membro Vida Consagrada"),
    ("901", "Estagiário"),
    ("902", "Médico Residente"),
    ("903", "Bolsista (Lei 8.958/94)"),
    ("904", "Participante de Curso de Formação (Res. CNSP)"),
    ("905", "Atleta não Profissional"),
]

SEFIP_CATEGORIA_TRABALHADOR = {
    "101": "01",
    "102": "01",
    "103": "07",
    "104": "06",
    "105": "01",
    "106": "01",
    "111": "01",
    "301": "01",
    "302": "01",
    "303": "01",
    "305": "01",
    "306": "01",
    "309": "01",
    "401": "26",
    "410": "01",
    "701": "13",
    "721": "11",
    "722": "05",
    "723": "13",
    "731": "17",
    "734": "22",
    "738": "24",
    "741": "13",
    "751": "13",
    "761": "13",
    "771": "13",
    "781": "13",
}

MODALIDADE_ARQUIVO = [
    (" ", "Recolhimento ao FGTS e Declaração à Previdência"),
    ("1", "Declaração ao FGTS e à Previdência"),
    ("9", "Confirmação de Informações Anteriores"),
]

CODIGO_RECOLHIMENTO = [
    ("115", "Recolhimento ao FGTS e Declaração à Previdência"),
    (
        "130",
        "Recolhimento ao FGTS e Informações à Previdência - Trab. Avulso Portuário",
    ),
    (
        "135",
        "Recolhimento ao FGTS e Informações à Previdência - Trab. Avulso Não Portuário",
    ),
    ("145", "Recolhimento ao FGTS - Diferenças"),
    ("150", "Recolhimento ao FGTS e Informações à Previdência - Obra/Construção Civil"),
    ("155", "Recolhimento ao FGTS - Emp. Contratante (Lei 6.019/74)"),
    ("211", "Declaração para a Previdência - Cooperativa de Trabalho"),
    ("307", "FGTS - Parcelamento de Débitos"),
    ("317", "FGTS - Parcelamento (Competências Anteriores)"),
    ("327", "FGTS - Parcelamento (Mês Rescisão/Dissídio)"),
    ("337", "FGTS - Parcelamento (Saldo Residual)"),
    ("345", "FGTS - Parcelamento de Débitos - Obra"),
    ("608", "Dirigente Sindical - Recolhimento ao FGTS"),
    ("650", "Recolhimento ao FGTS e Informações - Contingenciamento"),
    ("660", "Recolhimento ao FGTS - Anistia (Lei Complementar 110/01)"),
]

RECOLHIMENTO_FGTS = [
    ("1", "GRF no prazo"),
    ("2", "GRF em atraso"),
    ("3", "GRF em atraso com ação fiscal"),
    ("5", "Individualização"),
    ("6", "Individualização (retificação)"),
]

RECOLHIMENTO_GPS = [
    ("1", "GPS no prazo"),
    ("2", "GPS em atraso"),
    ("3", "Não gerar GPS"),
]

CENTRALIZADORA = [
    ("0", "Não centraliza"),
    ("1", "Centralizadora"),
    ("2", "Centralizada"),
]

OCORRENCIA_SEFIP = [
    ("01", "Não exposição a agente nocivo"),
    ("02", "Exposição a agente nocivo (aposentadoria esp. 15 anos)"),
    ("03", "Exposição a agente nocivo (aposentadoria esp. 20 anos)"),
    ("04", "Exposição a agente nocivo (aposentadoria esp. 25 anos)"),
    ("05", "Não exposição - múltiplos vínculos"),
    ("06", "Exposição 15 anos - múltiplos vínculos"),
    ("07", "Exposição 20 anos - múltiplos vínculos"),
    ("08", "Exposição 25 anos - múltiplos vínculos"),
]

DARF_CODES = {
    "employee": "0561",
    "director": "0588",
    "pss": "1661",
    "pss_patronal": "1769",
}
