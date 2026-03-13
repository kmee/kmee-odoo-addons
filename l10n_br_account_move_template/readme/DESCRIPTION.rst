Este módulo permite configurar templates de lançamentos contábeis de partida
dobrada baseados nos campos do documento fiscal brasileiro.

Funcionalidades principais:

* Templates hierárquicos (pai/filho) com herança de itens
* Mapeamento de ~40 campos fiscais (ICMS, IPI, PIS, COFINS, etc.) para contas
  de débito/crédito
* Geração automática de linhas no account.move ao postar a fatura
* Remoção automática ao voltar para rascunho
* Verificação de direito a crédito tributário (CST) para compras
* Cascade de resolução de contas: template → produto → parceiro → diário
