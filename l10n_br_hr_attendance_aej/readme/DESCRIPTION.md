Geração do **AEJ - Arquivo Eletrônico de Jornada** (Anexo VI da Portaria MTP
671/2021) e do **espelho de ponto** (art. 84).

O AEJ é o arquivo do **PTRP**, não do REP: é ele que carrega o tratamento -
marcações desconsideradas com motivo, inclusões manuais, ausências e banco de
horas - que o AFD, por ser imutável, não pode conter. O arquivo sai com os
registros 01 a 08 e o trailer 99, delimitados por pipe, em ISO-8859-1, e com o
fuso obrigatório em cada data e hora.

Pontos que o gerador trata com cuidado:

- **marcação desconsiderada não some**: entra como `tpMarc = "D"` com o motivo,
  porque tratamento sem rastro é o mesmo que adulteração;
- **`durJornada` em minutos** e horário contratual por padrão de escala, de
  modo que dias com jornadas diferentes tenham códigos diferentes;
- **assinatura CAdES** (`.p7s` destacado) com o certificado A1 do
  `l10n_br_fiscal_certificate`, reusando a gestão de certificado que a
  localização fiscal já mantém. Sem certificado, o arquivo é gerado mesmo
  assim, com aviso no chatter: serve para conferência interna, mas não para a
  entrega oficial dos arts. 86 a 88;
- **só gera de competência fechada**: arquivo entregue à fiscalização não pode
  mudar depois de emitido.

O **espelho de ponto** traz identificação, período, jornada contratual, todas
as marcações do dia (inclusive as de intervalo intrajornada, como exige o art.
74, § 2º da CLT) e a duração das jornadas, com a fonte de cada marcação
indicada.

O registro 08 identifica o PTRP e o seu desenvolvedor: preencha os parâmetros
`l10n_br_hr_attendance_aej.ptrp_*` com os dados de quem assina o Atestado
Técnico do art. 89.
