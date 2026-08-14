Eventos de Saúde e Segurança do Trabalho do eSocial (leiaute S-1.3).

Os intermediários seguem o padrão do ``l10n_br_esocial`` e reaproveitam o ciclo
de transmissão e de retorno já existente, inclusive o casamento do recibo pelo
``id_evento``.

* **S-2210** - Comunicação de Acidente de Trabalho, gerada a partir da CAT.
* **S-2220** - Monitoramento da Saúde do Trabalhador, gerado ao concluir o ASO,
  com os exames complementares da Tabela 27 e o médico coordenador do PCMSO.
* **S-2221** - Exame Toxicológico do Motorista Profissional (Lei 13.103/2015).
* **S-2240** - Condições Ambientais do Trabalho, com o grupo ``epiEpc``
  alimentado pela ficha de EPI e pelo Certificado de Aprovação, e **geração em
  massa** a partir do laudo: alterar o PGR ou o LTCAT de um ambiente gera o
  evento de todos os trabalhadores atingidos, com a mesma data de início.

**Validações antes do envio.** As regras que o eSocial só aponta na rejeição
rodam localmente: uso de EPI declarado sem entrega válida com CA, EPC ou EPI
implementado sem indicação de eficácia, ausência de agente nocivo convivendo com
proteção declarada ou com outros fatores de risco, e CAT de reabertura ou de
óbito sem o recibo da comunicação anterior. Descobrir isso no retorno custaria o
prazo legal.
