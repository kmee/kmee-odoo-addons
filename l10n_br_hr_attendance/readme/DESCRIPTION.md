Base do registro de ponto brasileiro conforme a Portaria MTP nº 671/2021.

Entrega a fundação que todos os demais módulos de jornada consomem:

- **Cadastro de REP** (`l10n_br.hr.rep`): equipamento (REP-C), conjunto
  autorizado (REP-A) ou programa (REP-P), com estabelecimento, identificação do
  fabricante e vigência do Atestado Técnico (art. 89).
- **NSR**: sequência por estabelecimento, iniciando em 1 e sem lacunas,
  reservada com bloqueio de linha para não colidir entre processos.
- **Marcação imutável** (`l10n_br.hr.marcacao`): o registro de origem não sofre
  `write` nem `unlink`. Corrigir é registrar um tratamento vinculado ao
  original, com autor e motivo, exatamente como o art. 82 determina ao PTRP.
- **Conciliação por CPF com fallback para PIS/PASEP**: marcação cujo documento
  não bate com nenhum funcionário fica pendente, nunca é descartada.
- **Flags de contrato**: dispensa de controle de jornada (art. 62 da CLT) e
  registro por exceção (art. 74, § 4º).

O `hr.attendance` do Odoo continua existindo como visão de sessão (par
entrada/saída) e é montado a partir das marcações pelo módulo de apuração.
