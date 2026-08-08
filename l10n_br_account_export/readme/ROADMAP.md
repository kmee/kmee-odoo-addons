## Layouts disponíveis

Cada layout é um módulo próprio, instalado conforme o sistema do escritório:

| Módulo | Sistema | Formato |
|---|---|---|
| `..._dominio` | Domínio (Thomson Reuters) | TXT delimitado por pipe |
| `..._dominio_completo` | Domínio, com plano de contas | TXT, dois arquivos |
| `..._alterdata` | Alterdata (WCont) | CSV com aspas |
| `..._sci` | SCI (Visual Sucessor / Único) | CSV, ponto decimal |
| `..._ignis` | IGNIS | CSV com campos de largura fixa |
| `..._conttroller` | Conttroller | CSV, débito e crédito em colunas |
| `..._contmatic` | Contmatic Phoenix | posicional, 332 |
| `..._questor` | Questor | posicional, 445 |
| `..._protheus` | TOTVS Protheus | posicional, 139 |
| `..._exactus` | Exactus | posicional, 180 |
| `..._mastercontabil` | Master Contábil | posicional, 121 |
| `..._systempro` | Systempro | posicional, 544 |
| `..._viasoft` | Viasoft | posicional |
| `..._nasajon` | Nasajon | posicional |
| `..._megacontabil` | Mega Contábil | registros por prefixo |
| `..._fortes` | Fortes AG | registros, extensão `.CT` |
| `..._prosoft` | Prosoft | registros `LC1`/`LC2` |
| `..._calima` | Calima ERP Contábil | registros de larguras distintas |
| `..._sankhya` | Sankhya | planilha XLSX |
| `..._oracle_gl` | Oracle GL Interface | planilha XLSX |
| `..._sap` | SAP | planilha XLSX |

## Como acrescentar um layout

1. Crie um módulo que dependa de `l10n_br_account_export`.
2. Acrescente o identificador ao campo `layout` da configuração, com
   `selection_add` e `ondelete` em `cascade`.
3. Implemente `_generate_<identificador>`, devolvendo uma lista de
   `(nome do arquivo, bytes)`. Use os utilitários de `format_helper` para
   campos posicionais, delimitados, valor e data.
4. Herde `LayoutCase` no teste, informando `_layout` e, se for posicional,
   `_fixed_width`. O contrato do chassi já cobre geração, determinismo,
   codificação, vazamento de separador, partidas múltiplas e conta sem de-para.

## Pendências gerais

- de-para de códigos de histórico padrão;
- centro de custo;
- cadastros auxiliares (participantes, terceiros, inventário);
- envio automático do arquivo ao escritório (hoje o arquivo fica anexado ao lote).
