Envia lançamentos contábeis do Odoo para os sistemas usados pelos escritórios de
contabilidade brasileiros, eliminando a redigitação no fechamento mensal.

Este módulo é o chassi: o lote de exportação, o controle do que já foi enviado, a
crítica antes de gerar e os utilitários de formatação de arquivo. Os layouts de
cada sistema ficam em módulos próprios.

- **Lote persistente**: período, diários e opções ficam gravados no registro, e
  não se perdem como aconteceria num assistente.
- **Um lançamento sai uma vez**: o vínculo é gravado no próprio `account.move`,
  então desfazer a exportação é voltar o lote para rascunho.
- **Crítica antes do arquivo**: conta sem código no plano do escritório e
  lançamento desbalanceado são apontados antes de qualquer arquivo sair.
- **Reexportar é permitido**: o período pode receber uma segunda remessa (com
  aviso), porque lançamentos entram depois do primeiro envio.
