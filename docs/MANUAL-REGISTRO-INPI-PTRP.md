# Manual: registro do PTRP no INPI

**Objetivo:** registrar no INPI o programa de computador que a KMEE usa como
**PTRP** (Programa de Tratamento de Registro de Ponto) e, mais adiante, como
**REP-P**, conforme a Portaria MTP nº 671/2021.

**Para quem executa:** quem for conduzir o depósito. O manual é
autossuficiente: não é preciso conhecer o código para executá-lo, mas as
decisões marcadas como **[decisão]** precisam vir do time técnico ou da
diretoria antes de começar.

**Tempo estimado:** meio dia de trabalho para preparar, mais 7 a 10 dias de
processamento do INPI.

---

## 1. Antes de tudo: o que o registro no INPI faz e o que não faz

Vale alinhar isso com quem pedir o registro, porque a confusão é comum.

**O que o registro faz:** prova autoria e anterioridade do programa, com data.
Protege por **50 anos** contados de 1º de janeiro do ano seguinte ao da
publicação ou, na falta desta, da criação (art. 2º, § 2º da Lei 9.609/98). Vale
nos países da Convenção de Berna.

**O que o registro não faz:**

- **não é homologação nem certificação**: o INPI não analisa se o programa
  atende à Portaria 671. Não há exame de mérito, e desde o e-RPC não existe
  nem a figura da exigência;
- **não substitui o Atestado Técnico** do art. 89, que é o documento que o
  empregador precisa ter para usar o sistema. O Atestado é emitido pela KMEE,
  não pelo INPI;
- **não impede que terceiros usem o código**, que é distribuído sob AGPL-3. O
  registro protege a autoria da obra, não restringe a licença que escolhemos.

**Quando o registro é obrigatório para nós:** apenas se a KMEE assumir o papel
de **REP-P** (art. 78 da Portaria 671), porque aí o número de registro no INPI
vai dentro do arquivo AFD. Para operar só como **PTRP**, o registro é
dispensável do ponto de vista da Portaria. Ainda assim vale fazer: é barato,
rápido e dá lastro documental à autoria.

---

## 2. Decisões que precisam estar tomadas antes de abrir o formulário

Levante estas respostas por escrito antes de começar. Mudar depois custa uma
petição de correção (código 747, R$ 210,00).

| # | Decisão | Quem responde |
| --- | --- | --- |
| D1 | **Título do programa** que constará do certificado, do AFD e do AEJ. Sugestão: algo estável, sem número de versão no nome | Diretoria e time técnico |
| D2 | **Titular**: KMEE (pessoa jurídica), com CNPJ | Diretoria |
| D3 | **Autores** (pessoas físicas): nome, CPF, nacionalidade, endereço e qualificação. Constam do certificado e não podem ser omitidos | Time técnico |
| D4 | **Data de criação** e **data de publicação** do programa. A de publicação não pode ser anterior à de criação | Time técnico |
| D5 | **Versão a registrar** (a linha de versão fechada, por exemplo `16.0.1`) | Time técnico |
| D6 | **Quem assina digitalmente** a Declaração de Veracidade, com certificado ICP-Brasil válido | Diretoria |

---

## 3. Pré-requisitos

1. **Certificado digital ICP-Brasil** (e-CNPJ da KMEE ou e-CPF de quem for
   assinar). O sistema **não aceita** assinatura avançada, incluindo a do
   gov.br. Confira a validade antes: certificado vencido inviabiliza o
   peticionamento no meio do caminho.
2. **Cadastro no e-INPI**: https://gru.inpi.gov.br/pag/ (opção "Cadastre-se
   aqui", tipo "Cliente"). Se a KMEE já tiver cadastro, use o existente.
3. **Validador de assinatura**: https://validar.iti.gov.br/ para conferir cada
   documento assinado antes de anexar.

---

## 4. Preparar a documentação técnica (a parte que exige cuidado)

O INPI **não recebe e não guarda** o código-fonte. Você envia apenas um
**resumo digital (hash)**, e a guarda do arquivo que gerou esse hash passa a
ser responsabilidade da KMEE. Em uma eventual disputa judicial, é esse arquivo
que prova o conteúdo registrado. Se ele se perder ou for alterado, o registro
perde utilidade probatória.

### 4.1 Montar o pacote

Use a versão exata que será registrada (a tag do repositório), incluindo os
módulos do PTRP:

```bash
cd kmee-odoo-addons
git checkout 16.0.1                      # a tag da versão a registrar

git archive --format=zip --prefix=ptrp-kmee-16.0.1/ 16.0.1 \
    l10n_br_hr_attendance \
    l10n_br_hr_attendance_afd \
    l10n_br_hr_attendance_apuracao \
    l10n_br_hr_attendance_aej \
    l10n_br_hr_attendance_integridade \
    > ptrp-kmee-16.0.1.zip
```

O INPI aceita arquivo único (PDF, DOC, TXT) ou vários arquivos compactados em
ZIP ou RAR. O ZIP acima atende.

### 4.2 Gerar o resumo hash

O INPI **recomenda SHA-512** ou algoritmo mais recente. Não use SHA-256 aqui:

```bash
shasum -a 512 ptrp-kmee-16.0.1.zip
```

Guarde a saída inteira (128 caracteres hexadecimais). É ela que vai no
formulário, junto com o nome do algoritmo (`SHA-512`).

> **Não confundir com o resumo interno do PTRP.** O módulo
> `l10n_br_hr_attendance_integridade` calcula um SHA-256 do escopo atestado,
> que serve para conferir, em cada servidor, se o código em execução é o
> homologado. São dois artefatos com finalidades diferentes:
>
> | | Resumo do INPI | Resumo do PTRP |
> | --- | --- | --- |
> | Algoritmo | SHA-512 | SHA-256 |
> | Objeto | o ZIP do código-fonte | os arquivos do escopo atestado |
> | Para que serve | provar autoria em juízo | conferir a versão em execução |
> | Onde aparece | formulário e-RPC | AEJ gerado e Atestado Técnico |

### 4.3 Guardar

Arquive o ZIP **intacto**, em pelo menos dois lugares (recomendação do próprio
INPI), junto com:

- o hash SHA-512 e o nome do algoritmo;
- o número da GRU e, depois, o número do registro;
- o manifesto interno gerado por
  `env['l10n_br.hr.ptrp.integridade'].imprimir_manifesto()`.

Sugestão de local: Drive da KMEE, pasta do produto, mais uma cópia fria. Não
deixe o ZIP apenas na máquina de quem executou o depósito.

---

## 5. Emitir e pagar a GRU

1. Acesse https://gru.inpi.gov.br/pag/ e faça login.
2. Selecione o serviço **"Pedido de Registro de Programa de Computador - RPC"**,
   **código 730**.
3. Valor vigente: **R$ 210,00** (Portaria INPI/PR nº 10, de 09/05/2025, em
   vigor desde 07/08/2025). A tabela de programas de computador é publicada
   sem coluna de valor com desconto e a nota do anexo diz que o desconto de
   50% não incide sobre todos os códigos: confirme na tela o valor devido para
   a KMEE antes de pagar.
4. **Anote o número da GRU** ("Nosso Número"): ele amarra a Declaração de
   Veracidade ao pedido.
5. Pague e aguarde a compensação antes de peticionar.

---

## 6. Assinar a Declaração de Veracidade (DV)

Esta é a etapa que mais gera retrabalho. Leia com atenção:

1. Baixe o arquivo da DV pelo link disponível na própria GRU ou no formulário
   e-RPC. A DV é **específica daquela GRU**.
2. Assine digitalmente com certificado ICP-Brasil.
3. Confira a assinatura em https://validar.iti.gov.br/.

> **Nunca refaça o arquivo da DV.** Ele já vem assinado digitalmente pelo INPI,
> e essa assinatura é validada no envio. Copiar o conteúdo para um documento
> novo, converter, imprimir e escanear, ou gerar um PDF "igual" invalida o
> documento e derruba o peticionamento. Baixe, assine e anexe **o mesmo
> arquivo**.

Se quem peticiona não for o titular, é preciso também uma **procuração
eletrônica** assinada pelo outorgante (a KMEE), anexada junto com a DV.

---

## 7. Peticionar no e-RPC

Acesse https://gru.inpi.gov.br/peticionamentoeletronico/ e preencha:

**Dados do titular**: KMEE, com CNPJ e endereço.

**Dados do autor** (botão "Adicionar Autor", um por vez): nome, nacionalidade,
CPF, qualificação física (há uma lista, com opções como "Analista de sistemas,
desenvolvedor de software..."), endereço, cidade, estado, CEP, país, telefone
e e-mail.

**Dados do programa**:

- **Data de Criação** e **Data de Publicação** (a de publicação, no mínimo,
  igual à de criação);
- **Título**: conforme a decisão D1;
- **Linguagem**: selecione e clique em "Adicionar Linguagem", repetindo para
  cada uma. Para o nosso caso: Python, XML e JavaScript, mais o que o time
  indicar. Há a opção `<Outros>` para escrever o nome de uma linguagem que não
  esteja na lista;
- **Campo de Aplicação** e **Tipo de Programa**: são listas pesquisáveis por
  palavra-chave, com múltipla escolha. Sugestões de busca: "administração de
  pessoal", "recursos humanos", "controle", "automação comercial". Escolha o
  que descreve o programa de fato;
- **Resumo hash**: cole o SHA-512 gerado no item 4.2 e informe o algoritmo.

**Anexos**: a DV assinada e, se for o caso, a procuração. Nenhum outro
documento é exigido, e o código-fonte não é enviado.

Confira tudo antes de transmitir: **não existe fase de exigência**, então erro
de preenchimento vira petição de correção paga.

---

## 8. Acompanhar

- O sistema envia mensagem a cada etapa concluída (pedido protocolado,
  pagamento conciliado, certificado emitido);
- a concessão é publicada na **RPI**, que sai às terças;
- o **certificado fica disponível no portal do INPI em até 10 dias**, com média
  de 7;
- acompanhe também pelo "Meus Pedidos" no e-INPI.

Ao receber, salve o certificado junto do ZIP e do hash (item 4.3) e comunique
o número de registro ao time técnico.

---

## 9. O que fazer com o número de registro

O número entra em três lugares, e é bom conferir os três:

1. **Cadastro do REP no Odoo** (menu Ponto, Registradores): campo "Registro no
   INPI", nos REPs do tipo REP-P;
2. **AFD**: o número vai no campo 7 do registro tipo 1 (cabeçalho) e compõe o
   nome do arquivo, no padrão `AFD<INPI><CNPJ>REP_P.txt`, conforme o item 10
   do Anexo V;
3. **AEJ**: o registro 08 identifica o PTRP e o desenvolvedor, pelos parâmetros
   `l10n_br_hr_attendance_aej.ptrp_*` do sistema.

---

## 10. Novas versões: quando registrar de novo

Não há limite de registros sobre o mesmo software, e cada versão pode ser
registrada separadamente. Mas **não é preciso registrar cada release**, e vale
separar os dois documentos, que têm regimes diferentes:

| | Registro no INPI | Atestado Técnico (art. 89) |
| --- | --- | --- |
| Emitido por | INPI | KMEE |
| Precisa de novo quando | o programa se torna outro (finalidade, plataforma ou arquitetura diferentes) | muda o **escopo atestado** |
| Correção de bug, tela, tradução | não exige | não exige |
| Mudança no leiaute do AFD/AEJ ou no motor de apuração | não exige | **exige revisão** |
| Como saber | avaliação do time | o resumo SHA-256 do módulo de integridade muda |

A regra prática: registre no INPI quando fizer sentido marcar uma nova
anterioridade (uma versão maior, uma reescrita relevante); revise o Atestado
quando o resumo do escopo atestado mudar.

---

## 11. Erros que custam tempo ou dinheiro

- **Refazer o arquivo da DV** em vez de assinar o baixado: derruba o
  peticionamento (item 6);
- **Perder ou alterar o ZIP** cujo hash foi depositado: o registro continua
  válido, mas fica sem serventia probatória;
- **Gerar o hash com SHA-256** em vez de SHA-512: o INPI recomenda SHA-512;
- **Errar título, autor ou datas**: correção é petição paga (código 747);
- **Certificado ICP-Brasil vencido** no meio do processo;
- **Confundir o resumo do INPI com o resumo do PTRP**: são artefatos
  diferentes, com algoritmos e finalidades diferentes (item 4.2).

---

## 12. Checklist

**Preparação**

- [ ] Decisões D1 a D6 respondidas por escrito
- [ ] Certificado ICP-Brasil válido e testado
- [ ] Cadastro no e-INPI ativo
- [ ] Tag da versão criada no repositório
- [ ] ZIP gerado a partir da tag
- [ ] SHA-512 do ZIP gerado e anotado
- [ ] ZIP arquivado em dois lugares

**Depósito**

- [ ] GRU código 730 emitida e paga, número anotado
- [ ] DV baixada, assinada e validada no ITI
- [ ] Procuração assinada, se aplicável
- [ ] Formulário e-RPC preenchido e transmitido

**Depois**

- [ ] Publicação acompanhada na RPI
- [ ] Certificado baixado e arquivado com o ZIP e o hash
- [ ] Número informado ao time técnico
- [ ] Número lançado no cadastro do REP no Odoo

---

## 13. Fontes

- [Lei nº 9.609/1998 (Lei de Software)](https://www.planalto.gov.br/ccivil_03/leis/l9609.htm)
- [Decreto nº 2.556/1998](https://www.planalto.gov.br/ccivil_03/decreto/d2556.htm)
- [INPI - Guia básico de programa de computador](https://www.gov.br/inpi/pt-br/servicos/programas-de-computador/guia-basico)
- [INPI - Perguntas frequentes sobre programas de computador](https://www.gov.br/inpi/pt-br/acesso-a-informacao/perguntas-frequentes/programas-de-computador)
- [INPI - Apresentação oficial do e-RPC](https://www.gov.br/inpi/pt-br/servicos/programas-de-computador/arquivos/guia-basico/apresentaoesoftware.pdf)
- [Portaria INPI/PR nº 10, de 09/05/2025 (tabela de retribuições vigente)](https://www.in.gov.br/web/dou/-/portaria-inpi/pr-n-10-de-9-de-maio-de-2025-628603493)
- [Portaria MTP nº 671/2021](https://www.normaslegais.com.br/legislacao/portaria-mtp-671-2021.htm)
